# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルではリポジトリの主要な機能追加・設計方針・注意点をコードから推測して記載しています。

## [Unreleased]

### Added
- パッケージ基盤を追加
  - パッケージ version を 0.1.0 として定義（kabusys.__version__）。
  - パッケージ公開 API として data / strategy / execution / monitoring を __all__ に公開。

- 環境設定・.env 自動読み込み機能（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
  - .env の解析強化:
    - export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを実装。
    - 無効行・コメント行のスキップ。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / データベースパス / 環境種別・ログレベルなどをプロパティ経由で取得。
  - 必須環境変数未設定時は明示的な ValueError を発生させる（_require）。

- AI 支援モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を計算。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB 比較）。
    - 銘柄ごと最大記事数・文字数制限（トークン肥大化対策）。
    - バッチ処理（最大 20 銘柄/回）とエクスポネンシャルバックオフによる再試行（429/ネットワーク/タイムアウト/5xx をリトライ対象）。
    - レスポンスの厳格なバリデーション（JSON 抽出・results リスト・code/score の妥当性検査）。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。
    - API キー注入可能（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照し、レジーム結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しは独自実装でモジュール間のプライベート関数を共有しない方針。
    - LLM 呼び出し失敗時はフェイルセーフで macro_sentiment = 0.0 を採用。
    - API キー注入可能（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得 → 保存（バックフィル・健全性チェックを実装）。
    - 最大探索範囲や健全性上限を設けて無限ループや異常値を防止。

  - ETL パイプライン（kabusys.data.pipeline と etl の再エクスポート）
    - ETLResult データクラスを提供（取得件数・保存件数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェック（quality モジュール）等の設計方針を反映。
    - DuckDB を前提とした最大日付取得やテーブル存在確認ユーティリティを実装。

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: 約1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を calc_momentum で計算。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高変化率を calc_volatility で計算。
    - Value: raw_financials から最新財務を取得し PER / ROE を calc_value で計算。
    - DuckDB のウィンドウ関数を活用し、データ不足時は None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応、入力検証あり）。
    - IC（Spearman の ρ）計算 calc_ic（欠損・同値・少数レコードの扱いを考慮）。
    - ランク付けユーティリティ rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
  - 研究用 API を __all__ でエクスポート。

### Changed
- 全体的な設計方針を明文化（コード内 docstring）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない実装方針を各種モジュールで採用。
  - 外部 API 失敗時はフェイルセーフにより処理継続（例: LLM 失敗 = 0.0 など）。
  - DuckDB 0.10 の制約（executemany に空リスト不可）を考慮した SQL 実装。

### Fixed
- （初期実装につき特定の「修正」は無し。挙動上の安全対策やログ出力を多数追加。）

### Security
- OpenAI API キー・各種トークンは環境変数で取り扱う設計。必須キーがない場合は明示的に例外を出すことで安全性を保証。

## [0.1.0] - 2026-03-28

初期リリース相当の機能群（上記 Unreleased の内容をパッケージ初期版としてリリース）。主な機能:
- 環境設定（.env 自動読み込み、Settings）。
- ニュース NLP スコアリング（score_news）。
- 市場レジーム判定（score_regime）。
- ETL パイプライン用ユーティリティ（ETLResult, 差分取得設計）。
- マーケットカレンダー管理（is_trading_day, calendar_update_job 等）。
- ファクター計算と特徴量探索（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary）。
- DuckDB を用いたデータ処理を前提とした堅牢な SQL 実装。
- OpenAI（gpt-4o-mini）との連携（JSON mode 利用、リトライ・バリデーション実装）。

Notes（注意事項）
- OpenAI の利用には OPENAI_API_KEY（または各関数への api_key 引数）が必須です。未設定時は ValueError が発生します。
- .env 自動読み込みはプロジェクトルートを基準に行われます。パッケージ配布後に動作させる場合、KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して読み込みを制御してください。
- DuckDB を前提とした SQL（テーブル名/スキーマ）設計になっています。データ格納スキーマが異なる場合は移植が必要です。
- AI 呼び出しは外部 API に依存するため、API レート制限やレスポンスフォーマットの変化に影響を受ける可能性があります。レスポンスのバリデーションとフォールバックを実装していますが、運用時は監視を推奨します。

Breaking Changes
- 初期リリースのため破壊的変更はなし。

-----

今後の予定（推測）
- strategy / execution / monitoring モジュールの実装拡充と統合テスト整備。
- モデルやプロンプト改善、API 呼び出しのしきい値・リトライポリシーのチューニング。
- テスト用フックの追加（HTTP クライアント・OpenAI 呼び出しのモック化補助）。
- ドキュメント（使用例・DB スキーマ・運用手順）の整備。