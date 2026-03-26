Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の形式に準拠しています。  

[Unreleased]
-------------

- （現在の開発ブランチに未リリースの変更はありません）

[0.1.0] - 2026-03-26
--------------------

Added
- 初回リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ初期化:
  - src/kabusys/__init__.py にて __version__ と主要サブパッケージを公開 (data, strategy, execution, monitoring)。
- 環境設定:
  - src/kabusys/config.py を追加。
  - .env / .env.local ファイルまたは OS 環境変数から設定値を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env 解析は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等をプロパティとして取得。未設定必須項目は ValueError を送出。
  - 有効な KABUSYS_ENV 値 (development, paper_trading, live) と LOG_LEVEL 検証を実装。
- AI モジュール:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を基にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメント（ai_score）を算出し ai_scores テーブルへ書き込み。
    - JST ベースのニュースウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST) を calc_news_window で提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・1銘柄あたり記事数/文字数制限・JSON 応答バリデーション・スコアクリップ ±1.0 を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。API 失敗時は当該チャンクをスキップして継続するフェイルセーフ設計。
    - テスト容易性のため _call_openai_api をモジュール内で分離しており、ユニットテストで差し替え可能。
    - score_news(conn, target_date, api_key=None) を公開（戻り値: 書き込んだ銘柄数）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）、JSON パース、リトライ、API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - レジーム合成ロジック（スコアクリップと閾値）とトランザクション（BEGIN/DELETE/INSERT/COMMIT）による冪等性を担保。
    - score_regime(conn, target_date, api_key=None) を公開（戻り値: 1 成功）。
- Research モジュール:
  - src/kabusys/research/factor_research.py
    - モメンタム (calc_momentum)、ボラティリティ/流動性 (calc_volatility)、バリュー (calc_value) を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、ma200、ATR20、平均売買代金、出来高比、PER/ROE 等を算出。データ不足時は None を返却。
    - 関数は prices_daily / raw_financials のみを参照し外部 API にはアクセスしない設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 (calc_forward_returns)、IC（スピアマンの順位相関）計算 (calc_ic)、ランク付けユーティリティ (rank)、ファクター統計サマリー (factor_summary) を実装。
    - horizons のバリデーション、単一クエリでの複数ホライズン算出、欠損処理等を含む。
  - research パッケージの __init__.py で主要関数を再エクスポート。
- Data モジュール:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB の値を優先し、未登録日は曜日ベースのフォールバックを使用。最大探索日数の上限制御を実装。
    - calendar_update_job による夜間バッチ更新（J-Quants API 経由、バックフィル、健全性チェック、冪等保存）を実装。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの骨格と ETLResult dataclass を実装。
    - 差分取得・保存（jquants_client 経由）・品質チェック（quality モジュール）との連携設計を反映。
    - ETLResult は to_dict で品質問題をシリアライズ可能。エラー/品質エラー有無の判定プロパティを提供。
  - src/kabusys/data/etl.py で ETLResult を公開再エクスポート。
  - DuckDB を主要な組込みデータベースとして使用。各書き込み処理はトランザクション（BEGIN/COMMIT/ROLLBACK）および部分更新戦略（DELETE → INSERT）で冪等性と部分失敗耐性を確保。
- テスト/運用性に配慮した設計:
  - LLM 呼び出し関数（_news_nlp._call_openai_api, regime_detector._call_openai_api 等）はモジュール内で分離されており、unittest.mock で差し替え可能。
  - 日付参照において datetime.today()/date.today() を直接参照しない関数設計によりルックアヘッドバイアスを防止（target_date を明示的に受け取る）。
  - OpenAI API のエラー処理は詳細に実装（RateLimitError, APIConnectionError, APITimeoutError, APIError の扱いと exponential backoff）。
- ロギング/警告:
  - 重要処理の INFO/DEBUG/WARNING ログを整備。例外時は適切に logger.exception / warnings.warn を使用。

Changed
- 新規リリースのため変更履歴なし。

Fixed
- 新規リリースのため修正履歴なし（実装時の堅牢化/フォールバック等を含む）。

Security
- OpenAI API キー（OPENAI_API_KEY）や Slack / Kabu API のシークレットは環境変数で管理する設計。Settings の必須プロパティは未設定時に ValueError を送出して安全性を担保。
- .env 読み込みで OS 環境変数を保護するため、.env.local の上書き挙動や protected set を考慮した実装。

Notes / Known limitations
- news_nlp の出力は現状 ai_score と sentiment_score が同一（将来的に差分化の余地あり）。
- バリューファクターでは PBR・配当利回りは未実装。
- DuckDB のバージョン差異によりリストバインドが安定しないため、DELETE/INSERT は executemany による個別実行で互換性を確保している（DuckDB 0.10 を想定した実装注意）。
- J-Quants 連携は jquants_client モジュールを通じて行う設計（本リリースでは参照実装を想定）。

参考・補助情報
- 自動 .env ロードはプロジェクトルートが検出できない場合スキップされます（パッケージ配布後の挙動を想定）。
- テストを書く場合、LLM 呼び出し箇所を patch して deterministic な応答を注入してください。
- 必要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY など。

以上。