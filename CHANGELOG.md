# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記録します。  
このプロジェクトはセマンティックバージョニング (https://semver.org/) を採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティ群の初期実装を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブモジュール構成: data, research, ai, monitoring, strategy, execution（__all__ に宣言）。

- 環境設定管理 (kabusys.config)
  - .env 自動読み込み機能（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env / .env.local の優先順位制御（OS環境変数保護、.env.local は override=True）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 高度な .env パース機能:
    - export KEY=val 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理。
  - Settings クラスによる環境変数ラッパー:
    - J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル等のプロパティ。
    - 値検証（無効な KABUSYS_ENV / LOG_LEVEL は ValueError）。
    - Path 型での duckdb/sqlite パス解決。

- AI モジュール
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI (gpt-4o-mini) の JSON mode を使い一括バッチでセンチメントを取得（銘柄ごと最大 _BATCH_SIZE=20）。
    - 時間ウィンドウ: JST 前日 15:00 〜 当日 08:30（UTC に変換して DB と比較）。
    - 1 銘柄あたり記事数 / 文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - レスポンス検証: JSON パース、results 配列、code/score の型チェック、未知コード無視、数値の有限性チェック。
    - スコアは ±1.0 にクリップ。取得したスコアのみ ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ（最大リトライ回数指定）。
    - テスト容易性を考慮し _call_openai_api をパッチ差替可能に実装。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - マクロニュース抽出はキーワードベース（_MACRO_KEYWORDS）で raw_news からタイトルを取得し、OpenAI（gpt-4o-mini）へ投げる。
    - レスポンスは JSON パースして macro_sentiment を抽出。API 失敗時はフェイルセーフで macro_sentiment=0.0。
    - レジームスコア合成、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しに対するリトライ / エラー処理を備え、テスト時に置換可能な _call_openai_api を使用。

- データ基盤ユーティリティ (kabusys.data)
  - ETL パイプライン基盤 (kabusys.data.pipeline)
    - ETLResult dataclass: ETL 実行結果の集約（取得/保存件数、品質問題、エラー一覧等）。
    - 差分取得 / backfill / 品質チェックを前提としたユーティリティ群（jquants_client と quality モジュールと連携）。
    - DuckDB に関する互換性考慮（executemany の空リスト制約など）。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job（J-Quants から差分取得・バックフィル・保存）。
    - 営業日判定ロジック:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバック、最大探索日数制限により安全性を確保。
    - 健全性チェック（未来日付の異常検知）と例外ハンドリング。

- 研究用ユーティリティ (kabusys.research)
  - factor_research: ファクター計算関数
    - calc_momentum: 1M/3M/6M リターン、ma200乖離（データ不足時は None）。
    - calc_volatility: 20日 ATR／相対ATR、20日平均売買代金、出来高比等。
    - calc_value: PER / ROE（raw_financials と prices_daily を組合せ）。
    - DuckDB を利用した SQL ベースの実装、外部 API 不使用。
  - feature_exploration: 分析ユーティリティ
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得可能。
    - calc_ic: スピアマンランク相関（Information Coefficient）の計算。3 銘柄未満で None を返す。
    - rank: 同順位は平均ランクにするランク変換（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Notes / 設計方針の要約
- ルックアヘッドバイアス防止のため、日付計算やクエリは target_date を明示的に受け取り、datetime.today() / date.today() を直接参照しない実装方針。
- 外部 API 呼び出しはフェイルセーフ（API 失敗時はスコアを 0.0 にフォールバック、処理継続）で設計。
- テスト容易性を意識し、OpenAI 呼び出し等は内部関数をパッチで差替え可能に実装。
- DuckDB の互換性と制約（executemany の空リスト等）に対応する実装上の配慮を行っている。

---

今後のリリースでは、以下のような項目が想定されます:
- モデル / プロンプト改善、スコアの校正
- J-Quants / kabu API クライアントの詳細実装と統合テスト
- 監視 (monitoring)・戦略 (strategy)・実行 (execution) モジュールの実装拡充
- ドキュメント補完・型注釈の強化・例外処理改善

（この CHANGELOG はコードから推測して作成しています。実際の変更・リリースノートは開発履歴に応じて調整してください。）