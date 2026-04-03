Keep a Changelog
=================

すべての重要な変更点をここに記録します。  
このプロジェクトは SemVer に従っています。  

フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（パッケージの公開インターフェースを定義）
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env/.env.local を自動読み込みする仕組みを実装（プロジェクトルートの検出は .git / pyproject.toml を利用）
  - export KEY=val 形式、シングル/ダブルクォート、インラインコメントの扱いに対応したパーサ実装
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB /監視 / システム設定値をプロパティで取得
  - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）
  - 環境変数の上書きポリシー（.env.local が .env を上書き、OS 環境変数は保護）

- データプラットフォーム（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult dataclass により実行結果・品質問題・エラーメッセージを集約
    - 差分取得、バックフィル、品質チェックの設計を反映
  - calendar_management
    - JPX カレンダー管理と営業日判定ユーティリティを実装
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新
    - market_calendar が未取得の場合は曜日ベース（土日休）でフォールバック
    - 検索上限・健全性チェック・バックフィルなどの保護ロジックを実装
  - ETL 用の公開型 ETLResult を kabusys.data.etl で再エクスポート

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出
    - バッチ処理（最大20銘柄/リクエスト）、1銘柄あたりの記事数/文字数上限（トリム）を実装
    - JSON mode のレスポンス検証・復元ロジック（前後余計テキストの回復）、スコアのクリップ処理
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ機構
    - スコアの書き込みは部分失敗時に既存スコアを保護する（DELETE→INSERT を対象コードのみ実行）
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を評価
    - prices_daily / raw_news を参照、OpenAI（gpt-4o-mini）を利用
    - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - API 呼び出し失敗時は macro_sentiment を 0.0 とするフェイルセーフ
    - LLM 呼び出しは内部で独立実装（モジュール間のプライベート関数共有を避ける）

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得し PER / ROE を算出（EPS=0/欠損は None）
    - DuckDB SQL を活用して効率的に算出。データ不足時の None 扱いを明確化
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（有効レコードが3未満なら None）
    - rank: 同順位は平均ランクにするランク変換（丸め処理で ties の誤検出を抑制）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数
  - zscore_normalize を kabusys.data.stats から再エクスポート（research/__init__ で公開）

Changed
- パッケージの設計方針を明示
  - 全ての時刻判定関数・スコアリング関数で datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）
  - DuckDB を主要なローカル分析 DB として利用する前提でクエリ最適化を行う
  - API 呼び出し周りは堅牢化（リトライ、レスポンス検証、部分失敗の保護）

Fixed
-（初版リリースのため該当なし。ただし各モジュールで想定されるエラー条件に対するハンドリングを多数追加）

Security
- 環境変数の自動ロードで OS 環境変数を保護する仕組みを導入（.env/.env.local が OS 環境を上書きしない）
- API キー（OpenAI 等）の要求は明示的で、未設定時は ValueError を発生させる（誤った無効な操作を早期に検出）
- .env ファイル読み込み失敗時は warnings.warn による通知（例外は上げずフォールトトレランスを確保）

Internal / Notes
- OpenAI クライアントとの相互作用は gpt-4o-mini と JSON mode を前提に実装
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持つ（モジュール結合を避ける）
- DuckDB executemany の空リストバインド制約に対応するため、書き込み前に params の非空チェックを行う
- calendar_update_job に健全性チェック（過度な将来日付のスキップ）とバックフィルを実装
- 一部の機能は外部 API（J-Quants / OpenAI / kabuステーション）に依存するため、必要な環境変数を設定すること
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings で要求されるプロパティ）
  - OpenAI: OPENAI_API_KEY（score_news / score_regime で必須）

Known issues / Limitations
- 一部の値（PBR・配当利回り等）は未実装（calc_value の拡張余地あり）
- news_nlp は LLM レスポンスフォーマットの揺らぎに対処する復元ロジックを持つが、完全な頑健性は保証しない
- calendar_update_job / ETL の jquants_client 呼び出しは外部 API に依存するため、ネットワーク/認証エラーは発生し得る（エラーはログに記録され処理は安全に中断）

迁移 / Upgrade Notes
- これは最初の公開バージョンです。次バージョンでは以下が追加される可能性があります:
  - 更なるファクター・リサーチ機能の追加
  - 発注（execution）モジュールの実装・強化（現状は公開インターフェースのみ）
  - 追加の品質チェックルールとモニタリング機能拡張

署名
- 初期リリース: kabusys 0.1.0（2026-04-03）