# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

Current: 0.1.0

## [0.1.0] - 2026-04-02
初回リリース。KabuSys のコア機能群を実装しました。主に日本株自動売買システム向けのデータ ETL、研究（リサーチ）ユーティリティ、ニュース系 AI スコアリング、マーケットカレンダー管理、設定読み込み周りを提供します。

### Added
- パッケージ基盤
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API に data, strategy, execution, monitoring を含めるエクスポートを定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは .git または pyproject.toml を起点に探索するため CWD に依存しない。
  - .env パーサーの実装：コメント行、export プレフィックス、クォート／バックスラッシュエスケープ、インラインコメント処理などに対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリ用の主要な設定をプロパティ経由で取得可能に：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時に ValueError を送出）。
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）、DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH の既定値を提供。
    - 環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）の検証（許可値チェック）を行うユーティリティプロパティ（is_live / is_paper / is_dev）。
    - リソース閾値（CPU / Memory / Disk）の取得（デフォルト値あり）。

- AI（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードを用いて銘柄ごとのセンチメント ai_score を生成。
    - バッチ送信（最大 20 銘柄／回）、記事トリミング（最大記事数・最大文字数）、エクスポネンシャルバックオフリトライ（429/ネットワーク断/タイムアウト/5xx）を実装。
    - API レスポンスの堅牢なバリデーション（JSON 抽出、results 配列・型検査、未知コード無視、数値チェック、±1.0 クリップ）。
    - 書き込みは部分失敗を考慮し、該当コードのみ削除→挿入の冪等方式で ai_scores を更新。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。OPENAI_API_KEY を環境変数で参照可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルに判定結果を保存。
    - マクロ記事はキーワードフィルタで抽出し（最大 20 件）、OpenAI（gpt-4o-mini）で macro_sentiment を評価。
    - API 呼び出し失敗時は macro_sentiment = 0.0 としてフェイルセーフ継続。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作。公開 API: score_regime(conn, target_date, api_key=None) → int。

- Data（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照して営業日判定機能を提供：
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にデータがない場合は曜日ベースでフォールバック（平日＝営業日）。
    - next/prev/get 関数は最大探索幅を設定し（_MAX_SEARCH_DAYS）無限ループを防止。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等的に更新（バックフィルや健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを追加し、ETL の取得数／保存数、品質チェック結果、エラー概要を集約。
    - ETL の設計方針・定数（データ開始日、バックフィル・カレンダー先読みなど）を定義。
    - 内部で jquants_client と quality モジュールを連携する前提の実装。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を prices_daily から計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（単純平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。欠損時は None。
    - calc_value: raw_financials から直近決算を結合し PER / ROE を計算（EPS が 0 または欠損なら PER は None）。
  - 特徴量探索・評価（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンの妥当性検証を実施。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。有効レコード 3 件未満は None。
    - rank: 平均順位を返すランク関数（同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

### Fixed
- （初回リリースにつき該当なし）

### Changed
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- OpenAI や J-Quants の API キーは環境変数を通じて注入する設計。Settings は必須変数が未設定の場合に明示的にエラーを出すため、誤設定に早期気づきやすくしています。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。テスト環境での誤読込み回避が可能です。
- OpenAI 呼び出し失敗時はフェイルセーフとして中立スコア（0.0）へフォールバックする実装があるため、AI API の断絶が即時に重大な破壊的操作に繋がるリスクを軽減します。

### Notes / Implementation details / 動作上の注意
- ルックアヘッドバイアス対策：AI／研究モジュール（score_news / score_regime / 各ファクター計算）は内部で datetime.today() や date.today() を参照せず、必ず caller が指定する target_date を基に計算します。
- DB 書き込みは冪等性を意識（DELETE→INSERT や ON CONFLICT による上書き想定）。部分失敗時の既存データ保護のため、書き込みコードは該当コードを限定して削除→挿入を行います。
- DuckDB との互換性に配慮し、executemany に空リストを渡さないチェックや日付型変換ユーティリティを用意しています。
- OpenAI 呼び出しのテスト容易性のために _call_openai_api はモジュール内で差し替え可能（unittest.mock.patch によりパッチ可能）な設計。

今後の予定（例）
- strategy / execution / monitoring 周りの実装拡充（発注ロジック、実運用モニタリング等）
- jquants_client の具体的実装、品質チェック（quality モジュール）の強化
- ドキュメント整備（API リファレンス、運用手順）

------------

参考: 主な公開関数 / クラス
- kabusys.config.settings (Settings)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.pipeline.ETLResult
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize

もしリリースノートに追加したい点（例: リリース日を別日付にする、詳細な破壊的変更情報を追記する、各関数の使用例を追加する等）があれば教えてください。必要に応じて追記します。