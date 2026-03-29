CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

Unreleased
----------

(なし)

0.1.0 - 2026-03-29
------------------

Added
- 初回リリース。KabuSys 日本株自動売買システムの基礎機能を実装。
- パッケージ情報:
  - パッケージバージョン: 0.1.0
  - モジュール公開: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env 読み込みの振る舞い:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォート無し値のインラインコメント認識（直前が空白/タブの場合）
    - ファイル読み込み失敗時に警告を出力
    - OS 環境変数を保護する protected 機能（.env.local は上書き可能だが OS 環境変数は保護）
  - Settings クラス提供（プロパティ経由での設定取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - データベースパスのデフォルト（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - ニュース収集ウィンドウ計算（JST 基準 → UTC naive datetime を返す calc_news_window）
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI (gpt-4o-mini) の JSON モードでバッチ評価
    - バッチサイズ、記事・文字数上限、JSON バリデーション、スコアクリップ（±1.0）などの実装
    - API 呼び出しのリトライ（429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフ）
    - レスポンスの保守的バリデーション（results 配列、各要素に code と score、未知コードの無視）
    - DuckDB へ書き込む際は部分失敗に備え、該当 code のみ DELETE → INSERT で置換（冪等性と部分失敗耐性）
    - テスト容易性のため _call_openai_api の差し替えを想定
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定
    - マクロキーワードによる raw_news フィルタリング（最大記事数制限）
    - OpenAI 呼び出し (gpt-4o-mini) と再試行ロジック（アプリケーションレベルのリトライと 5xx 判別）
    - レジームスコアのクリップ、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API 失敗時は macro_sentiment=0.0 のフェイルセーフ

- Data モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days 等の営業日判定ユーティリティ
    - market_calendar が未取得の場合は曜日ベース（土日除外）のフォールバック
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫性を保つ設計
    - 最大探索日数制限による無限ループ防止
    - 夜間バッチ calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新、バックフィル・健全性チェック実装
    - jquants_client 経由での取得・保存処理を利用
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー一覧などを保持）
    - 差分更新・バックフィル・品質チェックを考慮した ETL 設計（DataPlatform.md に準拠）
    - 内部ユーティリティ: テーブル存在チェック、テーブル最大日付取得、トレーディングデータの調整ロジック
    - jquants_client と quality モジュールを連携してデータ取得・保存・品質検査を実施
    - ETL 結果を辞書化する to_dict（quality_issues をシリアライズ）

- Research モジュール (kabusys.research)
  - factor_research
    - モメンタムファクター calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ / 流動性 calc_volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）
    - バリューファクター calc_value（PER、ROE、raw_financials からの最新財務データ利用）
    - DuckDB SQL を活用した一貫した実装（外部 API へはアクセスしない）
    - データ不足時の None 扱い（安全設計）
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、ホライズン検証）
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）
    - ランク変換ユーティリティ rank（同順位は平均ランク）
    - ファクター統計量 factor_summary（count/mean/std/min/max/median）
    - 外部ライブラリに依存せず純標準ライブラリで実装

- その他
  - DuckDB を主要な分析 DB として使用する設計に統一
  - 各所で詳細なログ出力を実装（info/debug/warning）
  - ルックアヘッドバイアス対策: 各種処理で datetime.today()/date.today() を参照せず、target_date を明示的に受け取る設計
  - テスト容易性: OpenAI 呼び出し箇所や内部関数の差し替えを想定した実装（ユニットテストでのモック利用を容易に）

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Deprecated
- （新規リリースのため該当なし）

Removed
- （新規リリースのため該当なし）

Security
- 特になし

Notes / Known limitations
- calc_value: PBR・配当利回り等は現バージョンでは未実装（注記あり）
- news_nlp / regime_detector は OpenAI API に依存。APIキー未設定時は ValueError を発生させる設計
- DuckDB executemany は空リストバインドに制約があるため、空チェックを導入している
- OpenAI レスポンスの頑健なパース処理を行っているが、LLM 出力の大幅な逸脱は完全には防げないためログでスキップする挙動を採用

Contributors
- 初回コードベース（実装作者はソースコメントに準拠）

---