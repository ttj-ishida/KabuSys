# Changelog

すべての主要な変更は Keep a Changelog の形式に準拠して記載しています。  
リリース日はコードベースから推測できる内容を基に設定しています。実際の公開日やリリース手順はプロジェクト運用に合わせて調整してください。

全般:
- DuckDB を中心としたデータ処理（prices_daily / raw_news / raw_financials / market_regime / ai_scores / market_calendar 等）を前提とした設計。
- OpenAI（gpt-4o-mini）を用いた NLP / センチメント処理を提供（JSON Mode を利用）。
- ルックアヘッドバイアス対策として date.today()/datetime.today() を直接参照しない設計思想を採用。
- テスト容易性のため、OpenAI 呼び出し箇所はパッチ差し替え可能（内部 _call_openai_api のモック等）。

[Unreleased]
- 監視 (monitoring) モジュールの具現化（パッケージ __all__ に含まれているが具体的実装は未配置）
- ETL パイプライン中の一部ファイルに記述途切れ / タイポの疑いあり（pipeline._get_max_date の末尾が不完全）。次回リリースで修正予定。
- jquants_client 等外部クライアントの実装確認および例外ハンドリング強化（現状は呼び出しに try/except を準備済み）。

[0.1.0] - 2026-03-31
Added
- パッケージ初期リリース相当の機能を追加（バージョン: 0.1.0）。
- 環境設定 / ロード
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml で検出）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env のパースは export 形式や引用符・エスケープ、コメント等の一般的なケースに対応する実装を提供。
  - Settings クラスを公開（properties による厳格な必須環境変数チェックを実装）。
  - 主要な環境変数（必須）：JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（メソッド引数でも指定可能）。
  - 任意の設定：KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL、DUCKDB_PATH、SQLITE_PATH、PID_FILE_PATH、閾値（CPU/MEM/DISK）。
- データ基盤関連（kabusys.data）
  - calendar_management: JPX カレンダー管理 / 営業日判定ユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースでフォールバック。
    - calendar_update_job による J-Quants からの差分取得・冪等保存ロジックを実装（バックフィル、健全性チェックあり）。
  - pipeline / etl: ETLResult をデータクラスとして公開し、ETL 実行結果の構造化および品質検査結果の格納方法を定義（quality チェック呼び出し想定）。
  - ETL に関する設計方針（差分更新、バックフィル、品質チェックの扱い、id_token の注入可能性など）を実装方針として盛り込む。
  - ETL の内部ユーティリティ（テーブル存在チェック、最大日付取得など）を実装（※ pipeline.py に実装途切れの箇所あり。要修正）。
- AI / NLP（kabusys.ai）
  - news_nlp.score_news:
    - raw_news + news_symbols を元に、ターゲット日（前日15:00 JST〜当日08:30 JST相当ウィンドウ）の記事を集約し、銘柄ごとに OpenAI でセンチメントスコアを算出して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数上限および文字数上限を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行。レスポンス検証（JSON 抽出、results 配列、コード照合、数値検証）を実施。スコアは ±1.0 にクリップ。
    - API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - calc_news_window: タイムウィンドウ計算ユーティリティを実装（UTC naïve datetime を返す仕様を明確化）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - MA 算出は target_date 未満データのみ使用（ルックアヘッド防止）。データ不足時は中立（1.0）を採用。
    - マクロ記事抽出はキーワードベースで raw_news からタイトルを取得し、OpenAI で JSON レスポンス（{"macro_sentiment": ...}）を期待して解析。
    - OpenAI 呼び出しでのリトライ方針、API レスポンスパース失敗時のフォールバック（macro_sentiment=0.0）を実装。
- 研究 / ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials の最新財務データと株価を組合せて PER / ROE を算出（EPS が 0/欠損時は None）。
    - SQL ウィンドウ関数を多用し DuckDB 上で効率的に計算。
  - feature_exploration:
    - calc_forward_returns: target_date から各ホライズン先のリターンを LEAD で取得。デフォルト horizons=[1,5,21]。
    - calc_ic: スピアマン（ランク）相関を実装し、3 件未満で None を返す安全設計。
    - rank / factor_summary: 同順位平均ランク、基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで実装。
- パッケージ公開インターフェース
  - top-level kabusys.__all__ に data, strategy, execution, monitoring を含めた構成（strategy / execution 実装ファイルはこのスナップショットでは未掲載の可能性あり）。

Fixed
- （初期リリースのため該当なし。なお一部ファイルに実装途切れのため次回リリースで修正予定。）

Changed
- （初期リリースのため該当なし）

Security
- OpenAI API キーや各種トークンは環境変数経由で必須チェック。設定が不足している場合は ValueError を送出することで、誤動作を防止。

注意 / 既知の制限（このコードベースから推測）
- pipeline.py の末尾に記述途切れ（date.fro のような不完全な行）が存在し、現状ではインポート時に SyntaxError/NameError などを引き起こす可能性がある。配布前に該当箇所の修正が必要。
- jquants_client や quality モジュール、monitoring モジュール等、外部依存あるいは別ファイルとして想定される部分の実装は本スナップショットには含まれていない。実稼働にはそれらの実装／設定が必要。
- OpenAI 呼び出しは gpt-4o-mini を想定しており、API の仕様変更やレスポンス形式の変更に依存する。JSON Mode を使っているが、万が一前後に余計なテキストが混ざる場合の復元処理を入れているものの、完全な保証はない。
- DuckDB のバージョン依存（executemany の空リスト制約など）に対する互換性考慮があるため、使用する DuckDB のバージョンに注意が必要。
- 全体的に「ルックアヘッドバイアス」対策が施されているが、データのタイムスタンプ管理（UTC/ローカル）、データ鮮度に起因する問題は運用ルールで補完する必要がある。

必要な環境変数（主要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY（score_news / score_regime は引数での注入も可能）
- 推奨 / 任意:
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
  - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env 読み込みを無効化する場合に 1 を設定）

開発者向けメモ
- OpenAI 呼び出し箇所（news_nlp._call_openai_api, regime_detector._call_openai_api）は unittest.mock.patch 等で差し替え可能にしてあるため、ユニットテスト作成時に API 呼び出しを簡単にモックできます。
- 各モジュールは「例外は上位へ伝播する箇所」と「フェイルセーフで継続する箇所」を明確に区別しているため、運用ポリシーに合わせたエラー処理の取り扱いを検討してください（例: ETL は品質問題があっても処理継続する設計）。

今後の予定（推奨）
- pipeline.py の不完全箇所修正と追加ユニットテストの整備。
- monitoring モジュール（プロセス・リソース監視、Slack 通知等）の実装。
- jquants_client / quality / その他外部クライアントのサンプル実装・ドキュメント追加。
- CI での DuckDB バージョン行き違いを防ぐためのテスト matrix 構築。

---

この CHANGELOG は提示されたコードから推測して作成しています。実際の変更履歴（コミットログ、リリースノート等）に基づく正式なドキュメント作成時は、該当情報に差し替えてください。