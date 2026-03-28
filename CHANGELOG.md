CHANGELOG
=========

すべての変更は Keep a Changelog ガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: 以下はリポジトリ内のコード内容から機能や設計方針を推測して作成したリリースノートです。実際のコミット履歴が存在する場合はそれに合わせて調整してください。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-28
-------------------

Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージバージョン: __version__ = "0.1.0"
  - パッケージ構成: data, research, ai, execution, strategy, monitoring 等のモジュールを公開

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
  - .env パーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）
  - 環境変数必須チェック（_require）と Settings クラスを提供
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - オプション: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH / SQLITE_PATH（デフォルトパス設定）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp.py）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ解析して銘柄ごとのセンチメント（ai_scores）を算出・保存する処理を実装
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに使用）
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・3000 文字でトリム
    - 再試行方針: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数設定）
    - レスポンス検証: JSON 抽出、results 配列、コード整合性、スコア型チェック、±1.0 でクリップ
    - DB 書き込みは部分置換（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護
    - テスト容易性: _call_openai_api をパッチ可能に設計

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ書き込み
    - MA200 乖離は target_date 未満のデータのみで算出（ルックアヘッド防止）
    - マクロニュース抽出はキーワードフィルタ（複数キーワードセット）と最大記事数制限
    - OpenAI 呼び出しは gpt-4o-mini の JSON モードを使用、リトライとフォールバック（失敗時 macro_sentiment=0.0）
    - スコア合成・閾値判定（bull / neutral / bear）と冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API キー未設定時は ValueError を送出

- データ基盤関連（kabusys.data）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルに基づく営業日判定ロジックを実装
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供
    - market_calendar が未取得のときは曜日ベースでフォールバック（平日を営業日とみなす）
    - 最大探索範囲を設けて無限ループを防止
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新、バックフィル／健全性チェックを実装
    - jquants_client 経由での fetch/save を想定（外部クライアントとの連携点）

  - ETL / パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを公開（target_date, fetched/saved counts, quality_issues, errors 等）
    - 差分更新・バックフィル・品質チェック方針を反映したユーティリティの土台を実装
    - DuckDB を前提としたテーブル存在チェックや最大日付取得ユーティリティを提供
    - デフォルトの最小データ日（_MIN_DATA_DATE）やバックフィル日数等の定数を定義

- リサーチ／因子モジュール（kabusys.research）
  - factor_research.py
    - Momentum（1M/3M/6M リターン、ma200_dev）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB SQL で計算
    - データ不足時の None 扱い、処理は prices_daily / raw_financials のみ参照
    - 実行結果は (date, code) を含む dict のリストで返却
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）
    - IC（Information Coefficient）calc_ic（スピアマンのランク相関をランク変換して算出。最小有効サンプル数チェックあり）
    - ランク関数 rank（同順位は平均ランク）
    - factor_summary（count/mean/std/min/max/median を算出）

- 汎用設計方針（コード全体に共通）
  - ルックアヘッドバイアスを避けるため datetime.today() / date.today() の直接参照を避ける設計（関数引数で target_date を受け取る）
  - DuckDB を主要なローカル分析 DB として利用（デフォルトパス: data/kabusys.duckdb）
  - OpenAI 呼び出しは gpt-4o-mini / JSON mode を利用し、レスポンス整形・バリデーションを明確に実施
  - 外部 API の障害に対してはフェイルセーフ（スコア 0.0 / 処理スキップ等）で継続する設計
  - テスト容易性を考慮して外部呼び出し箇所（_call_openai_api 等）を差し替え可能に実装

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし

Security
- 初期リリースのため該当なし

Notes / 要注意事項
- 実行前に必須な環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定してください。Settings クラスは未設定時に ValueError を投げます。
- .env/.env.local の読み込みはプロジェクトルート検出を行います。配布後や CWD が変わる環境下でも安定して動作するように実装されていますが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- OpenAI との連携は JSON mode を前提としており、レスポンスのパースやフォーマットに失敗した場合はログに WARNING を出しフェイルセーフ処理を行います。
- DuckDB の executemany に空リストを渡せない制約（一部バージョン）を考慮した実装が行われています。

今後の予定（例）
- モデルやプロンプトのチューニング
- エラー監視・メトリクスの追加（特に AI API 呼び出しの可観測性）
- ETL のスケジューリング／ジョブ管理の導入
- ユニット / 統合テストの拡充（外部 API モックを利用した CI／再現性確保）

-----