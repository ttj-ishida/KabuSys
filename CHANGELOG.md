CHANGELOG
=========

この CHANGELOG は Keep a Changelog のフォーマットに準拠しており、本リポジトリに含まれるソースコードから機能・設計意図を推測して記載しています。

[Unreleased]
------------

- （現時点のリリースはありません）

[0.1.0] - 2026-03-28
-------------------

初回リリース。主な追加内容と設計上の注記を以下にまとめます。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージ外部公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定関連 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出: __file__ を起点に親ディレクトリから .git または pyproject.toml を探索。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - 上書き挙動: override フラグと protected（OS 環境変数保護）による制御。
  - Settings クラスに主要設定をプロパティとして提供（必須項目は未設定時に ValueError を送出）。
    - 必須環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値を持つ設定: KABU_API_BASE_URL (http://localhost:18080/kabusapi)、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV 等。
    - KABUSYS_ENV の許容値: development, paper_trading, live。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL 検証。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む。
    - ウィンドウ定義: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 比較）。
    - バッチング: 最大 20 銘柄／API コール、1 銘柄あたり最大 10 記事・3000 文字でトリム。
    - リトライ戦略: 429（レート制限）・ネットワーク断・タイムアウト・5xx に対し指数バックオフでリトライ。その他エラーはスキップ（フェイルセーフ）。
    - レスポンス検証: JSON パース、"results" 形式、code の検証、スコアの数値性確認、±1.0 にクリップ。
    - DB 書き込みは部分的な失敗を避けるため、スコアを取得できた銘柄のみ DELETE → INSERT（BEGIN/COMMIT/ROLLBACK 対応）。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（内部 _call_openai_api のパッチ）。
    - API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window で定義するウィンドウから最大 20 件のタイトルを抽出し LLM に渡す。
    - LLM 呼び出しは gpt-4o-mini（JSON mode）、リトライ・5xx 判定・API エラーの分類を行い、全リトライ失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - ルックアヘッドバイアス防止の設計: datetime.today() 等を参照せず、target_date 未満のデータのみを参照。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターンを使用し、失敗時は ROLLBACK を行い例外を上位へ伝播。

- データ基盤 (kabusys.data)
  - ETL パイプライン (data.pipeline, data.etl)
    - ETLResult データクラスを導入し、取得数 / 保存数 / 品質問題 / エラー概要を収集・提供。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。品質チェックは致命的でも全問題を収集して呼び出し元判断に委ねる方針。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを実装。
  - カレンダー管理 (data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
      - DB にデータがある場合は DB 値を優先し、未登録日は曜日ベース（平日のみ営業）でフォールバック。DB が未取得でも一貫した振る舞いを維持。
    - calendar_update_job: J-Quants API（jquants_client.fetch_market_calendar）から差分取得して market_calendar を更新する夜間バッチ処理を実装。
      - lookahead (デフォルト 90 日)、バックフィル（直近 7 日）をサポート。
      - 健全性チェック（last_date が極端に未来ならスキップ）や API エラー時の安全処理を実装。

- リサーチ（kabusys.research）
  - ファクター計算 (research.factor_research)
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily / raw_financials から算出する関数を実装。
    - データ不足時は None を返す設計。戻り値は (date, code) を含む dict のリスト。
    - 計算窓・パラメータ（例: 200 日 MA、ATR 20 日等）は定数化。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、horizons 引数検証）。
    - IC（Information Coefficient）計算 calc_ic（スピアマン擬似実装：ランクへ変換して相関を算出）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク）。

Changed
- （初回リリースにつき過去からの変更はなし）

Fixed
- （初回リリースにつき過去バグ修正履歴はなし）

Security
- OpenAI API キー等秘密情報は環境変数による注入を想定。Settings は必須のキー未設定時に明示的にエラーを出す。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布先での挙動に注意（必要に応じ KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化）。

Notes / Usage hints
- DuckDB を使用するため、関数呼び出し時は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を渡す必要があります。
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を前提に実装されています。API レスポンスの形式や SDK の挙動変更によりパースやエラー処理が影響を受ける可能性があります。
- ETL や calendar_update_job 等の夜間バッチは外部 API（J-Quants、OpenAI、kabuステーション）に依存するため、実運用では API キー・エンドポイントやレート制限に注意してください。
- DuckDB に対する executemany の空リストバインド制約（DuckDB 0.10）に配慮した実装がされており、部分的な DB 書き込みの保護が行われています。

将来の作業候補（推定）
- strategy / execution / monitoring モジュールの実装拡張（本リリースではインターフェース公開のみ）。
- テストカバレッジの拡充（OpenAI 呼び出しのモック化を活用）。
- レスポンス検証・ロギングの強化、モニタリング用メトリクス出力。

--- 

（注）上記はソースコードの実装・ドキュメント文字列から推測してまとめた CHANGELOG です。実際のリリースノートや運用ポリシーはリポジトリ管理者の決定に従ってください。