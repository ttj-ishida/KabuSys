# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはまだ初期リリース段階です。日付はリリース作成時点のものを記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース。

### Added
- パッケージ骨格を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - モジュールの公開: data, strategy, execution, monitoring

- 環境変数 / 設定管理
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装（src/kabusys/config.py）
    - プロジェクトルート判定は .git または pyproject.toml を基準に行うため、CWD に依存しない
    - .env と .env.local の読み込み順序をサポート（OS 環境変数を保護）
    - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - export KEY=val、クォート／エスケープ、インラインコメント等に対応するパーサ実装
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 等のプロパティを提供
    - 環境変数の必須チェック（未設定時は ValueError）
    - env と log_level の値検証（許容値の定義）
    - is_live / is_paper / is_dev の補助プロパティ

- ニュース NLP（OpenAI を用いたセンチメント）
  - score_news 関数を実装（src/kabusys/ai/news_nlp.py）
    - 対象ウィンドウ計算（JST で前日15:00〜当日08:30 → UTC に変換）
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約（記事数・文字数トリムあり）
    - 最大 _BATCH_SIZE（20）銘柄ごとにバッチ送信し、JSON Mode を用いて厳密な JSON を期待
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフで再試行
    - レスポンス検証（results 配列、code/score フィールド、未知コードの無視、数値性検査）
    - スコアは ±1.0 にクリップ。成功した銘柄のみ ai_scores テーブルへ置換（DELETE → INSERT）
    - テスト容易性: OpenAI 呼び出しは _call_openai_api を通しパッチ差し替え可能
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして処理継続

  - calc_news_window ユーティリティを実装（ウィンドウ計算）

- 市場レジーム判定
  - score_regime 関数を実装（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - LLM には gpt-4o-mini を利用、JSON Mode 期待、レスポンスパース失敗や API 例外時には macro_sentiment=0.0 にフォールバック
    - ルックアヘッドバイアス対策: target_date 未満のデータのみ参照、datetime.today() を参照しない設計
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - リトライ・エラーハンドリングとログ出力の実装

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時は None）
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率などの計算
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算
    - DuckDB を利用した SQL ベース実装、外部 API に依存しない

  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト: 1,5,21 営業日）に対する将来リターンの計算
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）計算（有効サンプル数チェック）
    - rank: 同順位は平均ランクとして処理するランク変換ユーティリティ（丸めにより ties 対応）
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算

  - research パッケージ __all__ の整理（主要関数を再エクスポート）

- データプラットフォーム（Data）関連
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新 job 実装（calendar_update_job）
      - J-Quants から差分取得 → market_calendar へ冪等更新
      - バックフィル（直近 _BACKFILL_DAYS を再取得）、健全性チェック（未来日付閾値）
    - 営業日判定ロジック群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 未取得時の曜日ベースフォールバック実装（土日を非営業日扱い）
    - 最大探索日数制限で無限ループ防止

  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を実装（ETL 実行結果の構造化）
      - 取得数 / 保存数 / 品質チェック結果 / エラー一覧 を保持
      - has_errors / has_quality_errors / to_dict を提供
    - 差分取得、バックフィル、品質チェック（quality モジュール）の設計方針を実装に反映
    - DuckDB 互換性を考慮したテーブル存在チェック / 最大日付取得ユーティリティ

  - data パッケージの公開インタフェース整備（etl の ETLResult を再エクスポート）

- その他ユーティリティ
  - DuckDB の日付値変換やテーブル存在判定などの低レイヤ関数を各モジュールに実装
  - ログ出力（各処理の開始・完了・警告）を充実させ、異常時の情報把握を容易に

### Changed
- 初期リリースのため該当なし

### Fixed
- 初期リリースのため該当なし

### Deprecated
- 初期リリースのため該当なし

### Removed
- 初期リリースのため該当なし

### Security
- 初期リリースのため該当なし

---

注記（設計上の重要ポイント）
- ルックアヘッドバイアス対策: 主要な分析・スコアリング関数はいずれも内部で datetime.today()/date.today() を参照しない設計。必ず target_date を引数で与えることを想定。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を期待するが、実際の SDK やモデル挙動に応じてパースの保険措置（部分的に JSON を抽出）を行っている。
- DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT を想定）し、部分失敗時に既存データを不必要に消さない工夫あり。
- DuckDB バージョン差異への注意点（executemany の空リスト制約など）をコード内にコメントで記載。

もし特定のモジュールについてリリースノート（例えば API、関数の使用例、互換性注意点）をより詳細に出力したい場合は、対象モジュール名を指定してください。