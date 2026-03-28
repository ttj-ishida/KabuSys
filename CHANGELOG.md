# Changelog

すべての注目すべき変更を記録します。This project adheres to "Keep a Changelog" の方針で、セマンティックバージョニングを使用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムのコアライブラリを公開します。

### Added
- パッケージ初期化
  - kabusys パッケージを導入。__version__ を "0.1.0" に設定し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数から構成を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準）。
  - .env パーサーを実装（export 構文、シングル/ダブルクォート、エスケープ、インラインコメント取り扱い等に対応）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須設定取得用の _require と Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティを公開。
  - デフォルトの DB パス（DuckDB, SQLite）を設定。

- AI モジュール（kabusys.ai）
  - news_nlp（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し ai_scores に書き込む処理を実装。
    - タイムウィンドウ（JST: 前日15:00〜当日08:30 = UTC 前日06:00〜23:30）計算を提供（calc_news_window）。
    - バッチ処理（最大20銘柄／バッチ）、1銘柄あたりの最大記事数／文字数トリム、JSON Mode を利用したレスポンス処理を実装。
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフと最大試行回数を実装。
    - レスポンス検証機能を実装（JSON 構文回復、results フィールドの存在チェック、コード照合、数値チェック、±1.0 にクリップ）。
    - 部分失敗に備え、ai_scores テーブルへの書き込みは対象コードのみを DELETE → INSERT することで既存スコア保護。
    - テスト容易性のため、OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。

  - regime_detector（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュースは news_nlp のウィンドウ関数 calc_news_window を利用、指定キーワードでフィルタしたタイトルを LLM に投入してスコア化。
    - OpenAI 呼び出しに対するリトライ（指数バックオフ）とフェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - 計算結果は market_regime テーブルへ冪等に保存（BEGIN/DELETE/INSERT/COMMIT）。ログ出力あり。
    - テスト容易性のため、内部 OpenAI 呼び出しを差し替え可能。

- Research モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱い（None の返却）を明確化。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、ランク相関による IC 計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等の外部依存なしで実装し、計算上の注意点（horizons の検証など）を実装。

- Data モジュール（kabusys.data）
  - calendar_management
    - market_calendar に基づいた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB 無し時は曜日フォールバック（週末除外）。
    - JPX カレンダーの差分取得と夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で取得・保存、バックフィル・健全性チェックを含む）。
  - pipeline / etl
    - ETL パイプラインの結果表現 ETLResult を dataclass として実装し、取得数/保存数/品質問題/エラー等を集約。
    - ETL の差分更新方針、バックフィル、品質チェックとの連携設計が反映されたユーティリティを実装。
  - jquants_client など外部 API クライアントは data パッケージ内で想定（実装は別ファイル）。

- 共通設計方針（複数モジュール）
  - いずれのモジュールも datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。すべて target_date を外部から注入する API を採用。
  - DuckDB 周りの互換性ワークアラウンド（executemany の空リスト制約、list バインドの回避等）を考慮。
  - DB への保存はできる限り冪等に（DELETE → INSERT / ON CONFLICT）行う戦略を採用。
  - OpenAI 呼び出しはフェイルセーフ設計（API 失敗時に処理継続、部分失敗の許容）を採用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須としているため、実行時に未設定だと ValueError が発生します。
  - OpenAI を利用する処理（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY を必ず指定してください。未設定時は ValueError を送出します。
- .env 自動ロード:
  - プロジェクトルートはソース配置場所を基準に検出するため、パッケージ配布後も期待通りに動作する想定です。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルト DB パス:
  - DuckDB のデフォルトパスは data/kabusys.duckdb、SQLite は data/monitoring.db です（Settings.duckdb_path / sqlite_path）。
- OpenAI への JSON Mode レスポンスは厳密な JSON を想定していますが、実運用では前後ノイズを復元する処理も入れているため、多少のレスポンス不整合に対しても耐性があります。
- テストしやすさ:
  - OpenAI 呼び出し部位は内部関数をパッチすることでモック可能です（unit test での差し替えを想定）。

### Security
- （初回リリースのため公開すべき既知の脆弱性はなし。ただし API キー・シークレットは .env / 環境変数で安全に管理してください。）

---

今後の予定（想定）
- strategy / execution / monitoring パッケージの具象実装（注文ロジック・バックテスト・モニタリング連携）。
- jquants_client の具体実装とテストカバレッジ強化。
- 追加の品質チェックルールやETL監査ログ機能の拡張。

（貢献者、コミット一覧などはリポジトリの git 履歴を参照してください。）