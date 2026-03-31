CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-31
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買・リサーチ基盤のコア実装を追加。
  - パッケージ導入点
    - パッケージ情報: kabusys.__version__ = "0.1.0"、公開モジュール: data, research, ai, 等。
  - 設定・環境変数管理 (kabusys.config)
    - .env ファイルまたは環境変数からの設定読み込みを自動化（優先度: OS 環境変数 > .env.local > .env）。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない実装。
    - .env パーサは export 形式、クォート/エスケープ、インラインコメント処理などに対応。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供: 必須変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID など）取得メソッド、DUCKDB/SQLite パス、環境（development/paper_trading/live）とログレベル検証、is_live/is_paper/is_dev ユーティリティ。
  - AI（自然言語処理）モジュール (kabusys.ai)
    - ニュースセンチメントスコアリング (news_nlp.score_news)
      - raw_news と news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信。
      - バッチサイズ、文字数上限、記事数上限等の定数制御。
      - レスポンスの堅牢なバリデーション（JSON 復元ロジック、結果フィルタ、数値チェック、スコア ±1.0 クリップ）。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。フェイルセーフで失敗時は該当チャンクをスキップ。
      - DuckDB への書き込みは部分失敗に備え、該当銘柄のみ DELETE → INSERT の冪等更新を実行（トランザクションと ROLLBACK 対応）。テスト互換性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）。
      - 出力: 書き込んだ銘柄数を返す。
    - 市場レジーム判定 (regime_detector.score_regime)
      - ETF 1321（日経225 連動型）200日MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
      - prices_daily からの MA 計算は target_date 未満のデータのみを参照し、ルックアヘッドバイアスを防止。
      - マクロ記事抽出はマクロキーワードリストでフィルタし、OpenAI に JSON 応答を要求してスコア化。API 障害時は macro_sentiment=0.0 のフォールバック。
      - 計算結果は market_regime テーブルへ冪等書き込み（DELETE → INSERT をトランザクション内で実行）。
      - OpenAI 呼び出しはテスト時に差し替えやすい設計。
  - Research（因子・特徴量探索）モジュール (kabusys.research)
    - factor_research
      - calc_momentum: 1M/3M/6M リターンと ma200 乖離率を銘柄ごとに計算。データ不足時は None を返す仕様。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率など流動性・ボラティリティ指標を計算。入力データ不足は None を返す。
      - calc_value: raw_financials からの EPS/ROE を用い PER/ROE を計算（EPS が 0 または欠損時は None）。
      - 全関数は DuckDB（prices_daily / raw_financials）を参照し、外部 API へのアクセスはしない。
    - feature_exploration
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
      - calc_ic: スピアマン順位相関（Information Coefficient）を計算。サンプル不足時は None。
      - rank: 同順位は平均ランクを返す実装（浮動小数の丸めで ties の判定を安定化）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - 研究向けユーティリティ zscore_normalize は kabusys.data.stats から再エクスポート（kabusys.research.__init__）。
    - 依存は標準ライブラリ中心で、pandas 等に依存しないことを設計方針に明示。
  - Data（データ基盤）モジュール (kabusys.data)
    - calendar_management
      - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB（market_calendar）が未取得の場合は曜日（平日/週末）ベースでフォールバックする実装。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック、例外ハンドリング）。
      - 実装は最大探索日数やバックフィル日数などの安全策を備える。
    - pipeline / etl
      - ETLResult dataclass を提供（ETL の実行統計、品質問題、エラーリストを格納）。to_dict によるシリアライズ処理あり。
      - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した設計。jquants_client との連携を想定した保存ロジックの実装方針。
      - kabusys.data.etl は pipeline.ETLResult を公開再エクスポート。
  - 外部サービス連携の想定
    - DuckDB を主要な分析 DB として使用。
    - OpenAI（gpt-4o-mini）を NLP 解析に利用（JSON Mode を使用して厳格な機械可読レスポンスを期待）。
    - J-Quants クライアント（jquants_client）を通じた市場データ取得・カレンダー同期（クライアント実装は別モジュール想定）。
    - kabuステーション API の設定項目を準備（KABU_API_PASSWORD, KABU_API_BASE_URL）。
    - Slack 通知用の設定を準備（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - テスト・運用面の配慮
    - ルックアヘッドバイアス防止のため各処理は datetime.today()/date.today() を直接参照しない（target_date を明示的に受け取る）。
    - API キー注入が可能（関数引数で api_key を渡せる）で、モックやユニットテストが容易。
    - OpenAI 呼び出しポイントは patch で差し替え可能にしてテストを容易化。
    - 各 DB 書き込みはトランザクションで保護し、失敗時は ROLLBACK を試行してログ出力。
    - エラー発生時はフォールバック（ゼロスコアやスキップ）で継続するフェイルセーフ設計。
  - ドキュメント的コメント多数
    - 各モジュール・関数に詳細な docstring を追加。設計方針、処理フロー、戻り値、例外条件、テストに関する注意などを明記。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数およびシークレット管理について
  - OPENAI_API_KEY 等の必須シークレットは Settings の _require でチェックし、未設定時は ValueError を送出するため運用時の漏れを検出しやすくしている。
  - .env 自動読み込みは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / 開発者向け補足
- 必須環境変数（例）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
- デフォルト DB パス
  - DUCKDB_PATH= data/kabusys.duckdb（expanduser 対応）
  - SQLITE_PATH= data/monitoring.db
- 自動 .env ロードはプロジェクトルートが検出できない場合はスキップされるため、パッケージ化後の挙動に注意。
- DuckDB バインドや executemany の空リスト制約等、バージョン互換性についてコード内に注記あり（DuckDB 0.10 に言及）。

今後の予定（想定）
- J-Quants クライアントの実装・統合テスト強化
- モデルやプロンプトのチューニング、LLM 結果の品質検証
- ETL のスケジューリング、監視・アラート機能の拡充
- 発注/実行モジュール（execution）やモニタリング（monitoring）の具象実装の追加

---
この CHANGELOG は、提示されたソースコードから推測して作成しています。実際のコミット履歴が存在する場合は、そちらに合わせて更新してください。