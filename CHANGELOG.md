CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  
各リリースには追加 (Added)、変更 (Changed)、修正 (Fixed)、セキュリティ (Security) のカテゴリで記載しています。日付はコードベースから推測した初期リリース日を使用しています。

Unreleased
----------
- なし

[0.1.0] - 2026-03-28
--------------------

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開用の __init__（__version__ = "0.1.0"）を追加し、主要モジュール(data, strategy, execution, monitoring)をエクスポート。
- 環境設定管理モジュール (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
  - .env と .env.local の読み込み順序 (OS 環境変数 > .env.local > .env) を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化をサポート。
  - クォート付き/なしの .env 行パースを実装（export KEY=val、エスケープ、インラインコメント処理を含む）。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、環境/ログレベルの検証含む）。
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約し、銘柄別にニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（ai_scores）を生成・書き込み。
    - バッチサイズ、1銘柄あたりの記事数・文字数上限、JSON Mode 応答検証、スコアクリップ等を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。失敗時はフォールバック（部分スキップ）して継続する設計。
    - テスト容易性のため _call_openai_api を patch 可能にしている。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し、リトライ/フォールバックロジックを実装。
    - API 呼び出しの失敗時は macro_sentiment = 0.0 として継続するフェイルセーフを採用。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を DuckDB の SQL とウィンドウ関数で計算。
    - calc_volatility: ATR(20) / atr_pct、avg_turnover、volume_ratio を計算。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS=0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクを返すランク関数を実装。
  - research パッケージの __all__ に主要関数をエクスポート。
- Data モジュール (kabusys.data)
  - calendar_management:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等のマーケットカレンダー判定ユーティリティを実装。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末除外）を採用し、DB 登録の有無に依存しつつ一貫した振る舞いを保証。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック含む）。
  - pipeline / ETL:
    - ETLResult データクラスを追加（ETL 結果の構造化、品質問題・エラー集約、to_dict）。
    - _get_max_date 等の内部ユーティリティを実装。
  - etl.py で ETLResult を再エクスポート。
- ドキュメント的な設計注釈（モジュール内 docstring）を多数追加:
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない方針、DuckDB の executemany の挙動差異への対応、IDEMPOTENT な DB 書き込み方針、テスト用差し替えフック等を明記。

### Changed
- （初回公開のため該当なし）

### Fixed
- （初回公開のため該当なし）

### Security
- 環境変数の必須チェックを Settings._require で行い、未設定時には ValueError を投げる設計により、機密情報未設定による誤動作を早期に検出。
- .env ロード時に OS 環境変数を protected として上書きを防止する保護機構を実装。

Notes / 設計上の重要ポイント
- OpenAI API は gpt-4o-mini を想定し、JSON Mode（response_format={"type":"json_object"}）を利用。応答パースの堅牢化（前後テキスト混入時の最外 {} 抽出等）を行っている。
- LLM 呼び出し箇所には一貫してリトライとエラーハンドリングを実装し、API 側エラーで全体を停止させないフェイルセーフ設計。
- DuckDB を主要なローカルデータストアとして想定し、SQL + Python の組合せで計算/集約を行う。外部依存（pandas 等）を避ける設計。
- DB 書き込みは冪等性（DELETE→INSERT / ON CONFLICT DO UPDATE など）とトランザクション（BEGIN/COMMIT/ROLLBACK）で保護されている。
- テスト容易性を考慮し、OpenAI 呼び出しの内部関数はモジュールごとに patch 可能（例: unittest.mock.patch）な実装になっている。

今後の予定（想定）
- strategy / execution / monitoring モジュールの実装（現在はパッケージエクスポートに名前のみ存在）。
- ai/regime_detector と ai/news_nlp の評価精度向上やプロンプト改善、OpenAI モデル/パラメータのチューニング。
- ETL の詳細 pipeline 実装、品質チェック（quality モジュール）との連携強化。

----- 

この CHANGELOG は、提供されたコード内容から機能・設計意図を推測して作成した初期リリースノートです。必要であれば、日付や項目の追記・修正を行います。