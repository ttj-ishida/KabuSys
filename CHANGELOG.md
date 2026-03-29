CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。
このプロジェクトの初期バージョンは 0.1.0 です。

例:
- リリース日: YYYY-MM-DD
- 各セクションは Added / Changed / Deprecated / Removed / Fixed / Security を使用

Unreleased
----------
（なし）

0.1.0 - 2026-03-29
-----------------

Added
- パッケージ初回公開
  - src/kabusys 配下に主要サブパッケージを追加: data, research, ai, monitoring, strategy, execution（__all__ を公開）
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定値を自動ロードする仕組みを実装
    - プロジェクトルートを .git または pyproject.toml を基準に検出して .env / .env.local を読み込む
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env.local は .env より優先して上書き（ただし OS 環境変数は保護）
  - .env パーサ実装（クォート、エスケープ、export KEY=val、インラインコメントの取り扱いに対応）
  - Settings クラスを提供（必須キーチェック、既定値、値バリデーション）
    - 必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）へバッチで送信してセンチメントを取得
    - バッチサイズ、最大記事数・文字数、JSON Mode を利用したレスポンス検証、JSON 抽出ロジックを実装
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）: 指数バックオフ
    - レスポンスのバリデーションとスコアの ±1.0 クリップ、部分成功時に既存スコアを保護する DB 書き込み（DELETE → INSERT）
    - ルックアヘッドバイアス防止のため target_date ベースのウィンドウ計算（calc_news_window）
    - テストしやすさのため _call_openai_api の差し替えを想定
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定
    - マクロ記事の抽出、LLM 呼び出し（独立実装）、スコア合成、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ
- リサーチ（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR, avg turnover, volume ratio）、Value（PER・ROE）を DuckDB 上で計算
    - データ不足時は None を返す設計
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装
    - 将来リターン計算（任意ホライズン、入力検証）、IC（Spearman 相関）計算、統計サマリー、ランク処理（同順位の平均ランク）
    - 外部依存を持たず標準ライブラリで実装
- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar を使った営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 登録がない日や NULL 値は曜日ベースでフォールバック（週末は非営業日）
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存、バックフィルと健全性チェックを実装
  - pipeline / etl
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題やエラー一覧の保持）
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した ETL パイプライン設計（実装インターフェース）
  - jquants_client 用フックを利用する構成（外部 API 呼び出し箇所を分離）
- テスト容易性のための設計
  - OpenAI 呼び出しをモジュール内 private 関数として抽象化して unittest.mock.patch で差し替え可能にしてある箇所を多数用意
- エクスポート整理
  - ai/__init__.py, research/__init__.py, data/etl.py などで公共 API を再エクスポート

Fixed
- .env 読み込みの堅牢化
  - ファイル開放やエンコーディング問題発生時に警告を出して継続
  - OS 環境変数の保護（読み込み時に上書きされないよう protected set を導入）
- DuckDB 互換性に配慮した DB 操作
  - executemany に空リストを渡さないガード（DuckDB 0.10 の制約回避）
  - date 型の安全な取り扱い（_to_date ユーティリティ）
- OpenAI レスポンスの堅牢なパース
  - JSON mode でも前後に余計なテキストが混入するケースを想定して最外の {} を抽出する復元処理を追加
  - レスポンス不正時は例外ではなくログ警告してフェイルセーフでスキップまたは中立値（0.0）にフォールバック
- ルックアヘッドバイアス回避
  - 全ての時刻ロジックで datetime.today()/date.today() を直に参照しない方針を採用（target_date ベースでウィンドウを計算）

Security
- 環境変数読み込みにおいて OS の既存環境変数は既定で上書きされないよう保護
- 必須シークレットは Settings のプロパティで明示的に要求（未設定時は ValueError）

Changed
- 初回リリースのため該当なし

Deprecated
- 該当なし

Removed
- 該当なし

Notes / 実装上の注記
- OpenAI クライアントの呼び出しは gpt-4o-mini と JSON Mode（response_format={"type": "json_object"}）を想定しているが、SDK の将来的な仕様変更に対しては getattr による安全取得や例外ハンドリングで耐性を持たせている
- news_nlp / regime_detector は LLM の失敗を致命的にしない設計（運用継続重視）
- DB 書き込み操作は冪等性を重視（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の明示的制御）
- 日付・時間はすべて naive な date / datetime を使用し timezone 混入を避ける方針

今後の予定（短く）
- ETL パイプラインの具体的なスケジューリング実装と品質チェックルールの拡充
- 監視・アラート（monitoring）と実取引モジュール（execution, strategy）の実装・テスト強化
- OpenAI API 呼び出しのコスト最適化（バッチサイズ調整やモデル選択の柔軟化）

お問い合わせ
- バグ報告・要望は issue を作成してください。