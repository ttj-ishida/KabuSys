# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルはコードベース（初期リリース相当）の機能追加・実装内容をコードから推測してまとめたものです。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期構成
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - サブパッケージ公開: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。
  - .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
    - 行コメント・インラインコメントの扱い（クォート有無で挙動を分離）
    - 無効行はスキップ
  - 読み込み順: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
  - Settings クラスを提供し、各種必須設定をプロパティとして取得可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須チェック
    - KABUSYS_ENV（development, paper_trading, live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）の設定と Path 変換
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装（_request）:
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter 実装
    - 再試行ロジック（指数バックオフ、最大 3 回）を実装（408/429/5xx を再試行対象）
    - 401 受信時はトークン自動リフレッシュして一回リトライする仕組み
    - ページネーション対応（pagination_key 使用）
    - JSON デコードエラー・ネットワークエラーの適切なハンドリングとログ
  - 認証ユーティリティ: get_id_token（refresh_token から idToken を取得）
  - データ取得関数:
    - fetch_daily_quotes（OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性保証）:
    - save_daily_quotes → raw_prices に ON CONFLICT DO UPDATE
    - save_financial_statements → raw_financials に ON CONFLICT DO UPDATE
    - save_market_calendar → market_calendar に ON CONFLICT DO UPDATE
  - fetched_at を UTC ISO 形式で記録（Look-ahead バイアス追跡用）
  - データ変換ユーティリティ: _to_float / _to_int（堅牢な型変換と欠損ハンドリング）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news / news_symbols へ保存する処理の実装方針を実装
  - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成（トラッキングパラメータ除去）
  - 解析に defusedxml を使用して XML Bomb 等の攻撃に対処
  - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定してメモリ DoS を緩和
  - URL 正規化処理を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）
  - データベース保存はバルク挿入をチャンク化して効率的に実行し、挿入数を正確に把握する設計

- リサーチ（研究）用モジュール（src/kabusys/research/...）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離を計算）
    - calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - calc_value（最新財務から PER, ROE を計算）
    - DuckDB のウィンドウ関数を活用し、必要な過去ウィンドウを効率的に取得
  - feature_exploration:
    - calc_forward_returns（複数ホライズンの将来リターンを一括で計算、horizons 検証）
    - calc_ic（Spearman ランク相関による IC を計算、サンプル数閾値処理）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank（同順位を平均ランクで扱うランク化ユーティリティ）
  - 研究モジュールは pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の生ファクターを取り込み、ユニバースフィルタ・正規化処理を行い features テーブルへUPSERT
  - ユニバースフィルタ:
    - 最低株価 _MIN_PRICE = 300 円
    - 20日平均売買代金 _MIN_TURNOVER = 5 億円
  - 正規化: zscore_normalize を利用、対象カラムを指定して ±3 でクリップ
  - 日付単位で DELETE→INSERT のトランザクションによる置換（冪等性）

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し final_score を計算して signals テーブルへ書き込む
  - コンポーネントスコア:
    - momentum, value, volatility, liquidity, news（AI スコア）
    - 各コンポーネントは欠損値を中立 0.5 で補完
  - final_score の重みはデフォルト値を用意（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）
    - ユーザー指定 weights を受け付け、妥当性検査（負値/NaN/非数値を除外）と合計 1.0 への再スケールを実施
  - BUY シグナル生成:
    - デフォルト閾値 _DEFAULT_THRESHOLD = 0.60
    - Bear レジーム時（ai_scores の regime_score 平均が負かつサンプル数 >= 3）には BUY を抑制
  - SELL（エグジット）判定:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が threshold 未満
    - 保有ポジションで価格が欠損する場合は判定をスキップし、ログを記録
    - 将来的にトレーリングストップや時間決済の拡張を想定（未実装箇所に注記）
  - signals テーブルにも日付単位で DELETE→INSERT のトランザクション置換（冪等性）

### Security
- ニュース収集で defusedxml を利用して XML パースに対する安全対策を実施（XML Bomb 等の軽減）。
- news_collector において HTTP/HTTPS スキーム以外の URL を許可しない設計（SSRF 緩和方針がコメントに明記）。
- .env の読み込みで OS 環境変数を保護（読み込み時に protected set を用いた上書き制御）。

### Reliability / Robustness
- API クライアントでのレート制限・再試行・トークン自動更新（401 処理）により運用耐性を強化。
- DuckDB への保存処理は ON CONFLICT DO UPDATE を用いて冪等性を保証。
- データ欠損（価格欠損・財務データ欠損等）に対する辞退・ログ記録の実装。
- .env パーサはクォートやエスケープに配慮し、現場での設定ミスに対して寛容に動作するよう設計。

### Notes / 未実装・今後の改善点（コード上の注記より推測）
- strategy のエグジット条件に関して、トレーリングストップ（peak_price が必要）や保有日数による時間決済は未実装で今後の拡張候補。
- news_collector の詳細実装（RSS フィード取得の具体的な HTTP 実装・記事→銘柄紐付けロジックの完全な実装）はファイル末尾で途中になっている箇所があり、追加実装が見込まれる。
- data.stats の zscore_normalize 実装は別ファイルに存在する前提（インポートされ利用されている）。

---

（本 CHANGELOG は、提供いただいたコードからの推測に基づいて作成しています。実際のコミット履歴がある場合は、本内容を基に差分を調整してください。）