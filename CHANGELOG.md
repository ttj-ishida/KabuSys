Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。パッケージのバージョンは src/kabusys/__init__.py の __version__ に合わせて v0.1.0 を初期リリースとして記載しています。必要に応じて日付や「Unreleased」セクションを調整してください。

----------------------------------------------------------------------
CHANGELOG
----------------------------------------------------------------------

すべての変更は Keep a Changelog のフォーマットに従って記録しています。
http://keepachangelog.com/ja/1.0.0/

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の変更

----------------------------------------------------------------------
[0.1.0] - 2026-03-19
----------------------------------------------------------------------

Added
- パッケージの初期リリース。トップレベル情報:
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config):
  - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサ: コメント・export プレフィックス・シングル/ダブルクォート・エスケープ・インラインコメント処理に対応。
  - 環境変数取得ユーティリティと検証付き Settings クラス:
    - 必須環境変数の検査（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* など）。
    - デフォルト値の提供（KABU_API_BASE_URL、DB パス等）。
    - KABUSYS_ENV／LOG_LEVEL の許容値チェック、is_live/is_paper/is_dev のヘルパー。

- データ取得 / 保存 (kabusys.data.jquants_client):
  - J-Quants API クライアント実装:
    - 固定間隔の RateLimiter（デフォルト 120 req/min）によるスロットリング。
    - 冪等なページネーション取得対応（pagination_key）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx をリトライ対象）。
    - 401 受信時にリフレッシュトークンで id_token を自動リフレッシュして再試行。
    - レスポンス JSON デコード例外の明示的エラー。
  - fetch_* API: 株価日足、財務データ、マーケットカレンダーの取得関数を提供。
  - DuckDB への保存ユーティリティ:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE で冪等保存）。
    - fetched_at を UTC ISO8601 で記録。
    - PK 欠損行のスキップとログ警告。
  - 型変換ユーティリティ: _to_float / _to_int（厳密な変換ルールを実装）。

- ニュース収集 (kabusys.data.news_collector):
  - RSS フィードからのニュース収集モジュール（デフォルト RSS ソースを含む）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、スキーム/ホスト小文字化）。
  - 記事 ID を SHA-256（正規化 URL ベースのハッシュ）で生成して冪等性を確保する設計（ドキュメント記載）。
  - defusedxml を使用した XML パース、安全対策（XML Bomb 対応）、HTTP スキーム検証、受信最大バイト数制限（10MB）などの防御策。
  - DB へのバルク挿入のチャンク化、トランザクションまとめ、INSERT RETURNING による正確な挿入数取得設計。

- リサーチ機能 (kabusys.research):
  - ファクター計算 (kabusys.research.factor_research):
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200 日移動平均乖離）を計算。
    - Volatility: 20 日 ATR、atr_pct（ATR/close）、avg_turnover、volume_ratio を計算。
    - Value: PER（price/EPS、EPS が 0 または欠損の場合は None）、ROE を取得。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照する設計。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを算出（LEAD による実装）。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）を計算。データ不足時の None ハンドリング。
    - rank: 同順位は平均ランクで処理（丸めにより tie 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
  - zscore_normalize を含むユーティリティを re-export。

- 特徴量作成 (kabusys.strategy.feature_engineering):
  - 研究モジュールから得た raw ファクターをマージして features テーブルに保存する処理を実装。
  - ユニバースフィルタ:
    - 最低株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - Z スコア正規化（指定カラムに対して）、±3 でクリップ。
  - 日付単位での置換（DELETE + bulk INSERT）により冪等性と原子性を確保（トランザクション使用）。

- シグナル生成 (kabusys.strategy.signal_generator):
  - features と ai_scores を統合して銘柄別 final_score を計算し、signals テーブルへ保存するフローを実装。
  - コンポーネントスコア:
    - momentum, value (PER ベース), volatility (atr_pct 反転), liquidity (volume_ratio), news (AI スコアをシグモイド変換)。
  - スコア計算時の欠損補完: コンポーネントが None の場合は中立値 0.5 で補完して不当な降格を防止。
  - 重みの扱い:
    - デフォルト重みを持ち、ユーザー指定 weights を検証・補完し、合計が 1.0 でなければ再スケール。
    - 無効値は無視しログ警告。
  - Bear レジーム検知: ai_scores の regime_score の平均が負かつサンプル数 >= 3 の場合 BUY を抑制。
  - SELL（エグジット）ルール:
    - ストップロス（終値/avg_price - 1 < -8%）を最優先。
    - final_score が閾値未満（デフォルト閾値 0.60）で SELL。
    - 一部未実装の条件（トレーリングストップ、時間決済）は doc に注記。
  - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性と原子性を確保。

- その他
  - 各モジュールで logging を活用し、操作情報・警告・デバッグを出力する実装。
  - DuckDB を前提とした SQL 実装（ウィンドウ関数、LEAD/LAG、AVG OVER 等）で高性能な集計を実現。

Security
- news_collector: defusedxml による安全な XML パースや受信サイズ制限など、外部入力に対する防御を導入。
- jquants_client: id_token リフレッシュ時や HTTP エラー処理で情報漏洩しないよう例外・ログの扱いに配慮（トークンの自動管理はモジュール内キャッシュで扱う）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Limitations
- 一部仕様（例: トレーリングストップ、時間決済の自動実装）は README/StrategyModel.md にて将来の拡張として明記されています（signal_generator の docstring 参照）。
- DuckDB のスキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本 changelog には含めていません。実運用前にスキーマ定義（DDL）を準備してください。
- NewsCollector の記事 ID 生成やニュース→銘柄紐付けの詳細実装は docstring に設計方針が示されています（実装箇所の継続実装が必要な場合は追って実装・改訂してください）。

----------------------------------------------------------------------
今後のリリースで検討する改善案（候補）
- SignalGenerator: トレーリングストップ・時間決済の実装（positions テーブルの peak_price / entry_date を活用）。
- NewsCollector: 複数フィード設定 UI、自然言語処理による記事の銘柄マッチング強化。
- Telemetry/モニタリング: execution 層や発注成功/失敗のトラッキング（monitoring パッケージの拡張）。
- テストカバレッジ拡充（ユニットテスト・統合テスト・DuckDB を用いた回帰テスト）。

----------------------------------------------------------------------

（必要であれば、この CHANGELOG をリポジトリのルートに追加し、リリースタグ v0.1.0 を作成してください。）