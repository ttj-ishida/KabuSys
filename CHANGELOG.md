Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
規約: https://keepachangelog.com/ja/1.0.0/

[Unreleased]


[0.1.0] - 2026-03-19
--------------------

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しました。
主な追加点と設計上のポイントを以下にまとめます。

Added
- パッケージ初期化
  - kabusys パッケージの __version__ を 0.1.0 として定義。
  - パブリック API: data, strategy, execution, monitoring を __all__ で公開。

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理をサポート。
  - 環境設定取得用 Settings クラスを提供。必須キー取得時は _require() により未設定で ValueError を送出。
  - 各種設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL にデフォルト値を設定。
    - DB パス: DUCKDB_PATH / SQLITE_PATH のデフォルトを設定。
    - KABUSYS_ENV に対する値検証 (development / paper_trading / live) と LOG_LEVEL 検証。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
  - リトライ（指数バックオフ）実装: 最大 3 回、408/429/5xx を対象。429 の Retry-After を優先。
  - 401 受信時は ID トークンを自動リフレッシュして再試行（無限再帰防止）。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を用いて重複を排除
    - PK 欠損行のスキップ、挿入件数のログ出力
  - 数値変換ユーティリティ: _to_float, _to_int（不正値・空値に頑健）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する処理を実装。
  - 記事 ID は URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を保証。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ削除（utm_*, fbclid 等）、フラグメント除去、クエリソート。
  - セキュリティ対策: defusedxml を使用して XML 攻撃を緩和、受信バイト上限（10MB）を設置、SSRF に対する検討（URL 検証ロジックを含む設計）、バルク挿入のチャンク化。
  - INSERT RETURNING を活用し、実際に挿入された件数を正確に返す設計（パフォーマンス考慮）。

- リサーチ / ファクター計算 (kabusys.research.*, kabusys.research.factor_research)
  - ファクター計算モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA のカウントチェックを含む）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true range の NULL 伝播を制御）
    - calc_value: per, roe（raw_financials の target_date 以前の最新レコードを取得）
  - 特徴量探索モジュール:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に1クエリで取得（リード関数を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（ties を平均ランクで処理）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにする実装（丸め処理による ties 検出対策あり）。
  - Research モジュールは外部依存を増やさず（pandas 等不使用）に設計。

- 戦略層 (kabusys.strategy)
  - 特徴量作成 (feature_engineering.build_features)
    - research モジュールから生ファクターを取得し、株価・流動性によりユニバースフィルタを適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats を利用）し ±3 でクリップ。
    - features テーブルへ「日付単位の置換」（BEGIN/DELETE/INSERT/COMMIT）で冪等かつ原子性を保証。
    - ユニバース判定閾値: 最低株価 300 円、20日平均売買代金 5 億円。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントを計算。
    - コンポーネント変換: Z スコア -> シグモイド、PER は逆数スコア化等を実装。
    - 重みの検証と正規化（デフォルト重みを用意、ユーザ入力は検証して合計が 1.0 になるよう再スケール）。
    - Bear レジーム判定: ai_scores の regime_score 平均が負であれば BUY シグナルを抑制（サンプル不足時は抑制しない）。
    - エグジット条件（SELL）:
      - ストップロス: 終値 / avg_price - 1 < -8%
      - スコア低下: final_score が threshold 未満
      - SELL 判定は BUY より優先し、signals テーブルへ日付単位の置換で保存（冪等）。
    - 欠損データに対する中立補完（None -> 0.5）を実装し欠損銘柄の不当な降格を防止。

Changed
- （初版のためなし）

Fixed / Robustness improvements
- DuckDB クエリや保存処理での欠損データ（PK 欠損、価格欠損、非数値）を適切にスキップ・ログ出力するよう設計。
- トランザクション失敗時の ROLLBACK 呼び出しをハンドリングし、ROLLBACK 失敗のログ化を行う。
- HTTP リクエスト周りで JSON デコード失敗時に詳細なエラーを出す設計。

Security
- news_collector で defusedxml を使用して XML の脆弱性を軽減。受信サイズ上限を設定し大容量攻撃を緩和。
- J-Quants クライアントはトークン自動リフレッシュを実装し、allow_refresh フラグで再帰を防止。
- .env ロードで OS 環境変数を保護する protected キーの概念を導入（.env.local の override 動作制御）。

Performance
- 各種データ取得・集約は可能な限り SQL ウィンドウ関数 / 単一クエリで処理（calc_forward_returns やファクター計算など）。
- 保存処理は executemany によるバルク挿入、news_collector はチャンク化して SQL 長制限を回避。
- API レート制御を組み込み、スロットリングで安定稼働を狙う。

Notes / Migration / Requirements
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
- research/* モジュールは外部ライブラリに依存しない設計（ただし news_collector は defusedxml を利用）。
- execution / monitoring パッケージは公開されているが、このリリースのコードスニペットでは中身の実装は省略または別ファイルに分離されています。

Acknowledgements
- このリリースはシステム設計ドキュメント（StrategyModel.md, DataPlatform.md 等）を参照して実装されています。今後のリリースでは実行層（発注 API 統合）、追加リスク管理ルール（トレーリングストップ、時間決済）等を実装予定です。