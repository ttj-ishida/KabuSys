# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]
（現時点のコードベースはリリース済みバージョン 0.1.0 に対応しているため未リリース項目はありません）

## [0.1.0] - 2026-04-03
初回リリース。日本株のデータ取得・ETL・特徴量（リサーチ）・AIベースのニュース解析・市場レジーム判定・カレンダー管理など、自動売買/リサーチ基盤のコア機能を実装。

### Added
- パッケージメタ
  - 初期バージョン設定: kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）
  - 公開モジュール群: data, strategy, execution, monitoring を __all__ で定義。

- 設定/環境変数管理（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準に探索）。
  - .env / .env.local の読み込み順序を実装（OS 環境変数を保護しつつ .env.local で上書き可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 高度な .env パーサ: export 形式、シングル/ダブルクォート内のエスケープ処理、コメント扱いの細かな仕様に対応。
  - Settings クラスを追加。J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル等のプロパティを提供。未設定の必須環境変数に対するエラー報告関数 _require を提供。
  - env 値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。

- データ収集・ETL（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
  - ETLResult データクラスを実装（ETL 実行結果・品質問題・エラーを集約し to_dict に変換可能）。
  - 差分更新・バックフィル・品質チェックを想定した ETL 設計（J-Quants クライアント経由での差分取得 / idempotent な保存を想定）。
  - ETL ユーティリティの公開インターフェース ETLResult を re-export（src/kabusys/data/etl.py）。

- マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
  - market_calendar テーブルを利用した営業日判定ロジックを実装:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - DB にカレンダーがない場合は「土日を休業日とする」フォールバックを採用。
  - calendar_update_job を実装（J-Quants API から差分取得し冪等保存、バックフィル、安全性チェックを行う）。
  - 最大探索日数やバックフィル日数などの安全パラメータを実装（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。
  - DuckDB からの date 変換ユーティリティ _to_date を実装。

- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - score_news を実装:
    - 指定日の前日 15:00 JST ～ 当日 08:30 JST のニュースを対象に集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄／コール）、1銘柄あたり記事数・文字数上限でトリム。
    - 再試行（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）とフェイルセーフ（API 失敗時はそのチャンクをスキップして処理継続）。
    - レスポンスの厳密バリデーションとスコアの ±1.0 クリップ。
    - DB への書き込みは部分失敗耐性を持たせる（書き込み前に対象 code の DELETE → INSERT）。
  - calc_news_window を実装（UTC naive datetime を返す。JST ベースのウィンドウ計算）。
  - 内部の OpenAI 呼び出しラッパーとレスポンス検証ロジックを実装（テスト時のパッチ差し替えを想定）。

- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - score_regime を実装:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini）による JSON 出力のパース、再試行・フェイルセーフを実装。
    - DB へは冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う。
    - モジュール間結合を避けるため、news_nlp とは別実装の OpenAI 呼び出しラッパーを使用。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算（データ不足時の None ハンドリング）。
    - calc_volatility: 20日 ATR、ATR/価格 比、20日平均売買代金、出来高比率を計算（NULL/データ不足に対する取り扱い）。
    - calc_value: raw_financials から最新の EPS/ROE を取得して PER/ROE を計算（EPS 0 や欠損時は None）。
    - DuckDB ベースの SQL 処理で高速性と一貫性を重視。
  - feature_exploration.py:
    - calc_forward_returns: 指定日から将来ホライズン（デフォルト [1,5,21]）までのリターンを一括取得。
    - calc_ic: スピアマンのランク相関を使った IC 計算（ties 平均ランク処理、データ不足時は None）。
    - rank: 同順位は平均ランクを返すランク関数（丸めによる tie 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ関数。
  - いずれも「datetime.today()/date.today() を参照しない」設計で、ルックアヘッドバイアスを防止。

- 研究用ユーティリティ再エクスポート（src/kabusys/research/__init__.py）
  - 代表的な関数群を __all__ で公開（zscore_normalize の再エクスポート等）。

### Changed
- 設計方針（全体）
  - 多くの処理で「ルックアヘッドバイアス防止」を明示的に採用。target_date を呼び出し元が提供し、内部で現在時刻を参照しない設計を採用。
  - OpenAI 呼び出しの失敗を個別チャンクでフェイルセーフに扱うことで、一部 API 障害時も他データを書き込める堅牢性を確保。
  - DuckDB の executemany に関する互換性問題（空リスト不可）への対策を各所に導入。

### Fixed
- エラーハンドリング / ロギングの強化
  - DB 書き込み失敗時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出力するように改善（news_nlp, regime_detector, pipeline 等）。
  - OpenAI レスポンスの JSON パース失敗時に復元を試みる処理（最外側の {} を抽出）を news_nlp で実装。

### Security
- 環境変数取り扱いの注意
  - Settings._require による必須環境変数の明確化とエラーメッセージで、秘密情報未設定時の早期検出を促進。
  - OS の既存環境変数を保護する protected 機構により .env で誤って上書きするリスクを低減。

### Notes / Implementation Decisions
- OpenAI クライアント呼び出しは各モジュールで独立したラッパー関数を持ち、モジュール間で private 関数を共有しない（疎結合化）。
- DuckDB を主要なローカル分析 DB として想定。SQL と Python を組み合わせた実装でパフォーマンスと可読性を両立。
- API キーは関数引数で注入可能（テスト容易性向上）かつ、引数がない場合は環境変数 OPENAI_API_KEY を参照。
- ETL / カレンダー / AI 系処理は全て「冪等性」「部分失敗耐性」「ログ出力による可観測性」を重視している。

-----

以上が v0.1.0 の主要な追加・変更点です。今後のリリースではドキュメント整備、ユニットテストの追加、エラーレポーティングの強化、OpenAI モデルの差し替え・設定可視化、kabu ステーション / LINE 通知の統合などが想定されています。