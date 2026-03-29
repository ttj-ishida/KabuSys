# Changelog

すべての重要な変更をこのファイルに記録します。本プロジェクトは Keep a Changelog の慣習に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、以下は提供されたコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]
- 現時点の差分はありません。

## [0.1.0] - 2026-03-29
初回リリース。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期実装（__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local を自動で読み込む仕組みを実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーを実装（export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応）。
  - 環境変数読み取り用 Settings クラスを提供。J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live）等のプロパティを定義。
  - 必須環境変数未設定時は ValueError を投げる _require を実装。

- AI (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄別に記事をまとめ、OpenAI（gpt-4o-mini）に送ってセンチメント（-1.0〜1.0）を算出する score_news 実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄）・1銘柄あたり記事数/文字数制限・JSON Mode 利用。
    - リトライ（429/ネットワーク/タイムアウト/5xx）および指数バックオフ実装。API エラー時はスキップして継続するフェイルセーフ設計。
    - レスポンスのバリデーションを実装（JSON 抽出、results 配列、コード整合性、数値型チェック、スコアの ±1.0 クリップ）。
    - DuckDB への書き込みは冪等（DELETE → INSERT、部分失敗で既存スコアを保護）で実装。
    - テスト容易性のため _call_openai_api をモック差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily からの MA200 乖離計算、raw_news からのマクロキーワード抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを含むフローを実装。
    - OpenAI 呼び出しは独立実装とし、API 失敗時には macro_sentiment=0.0 とするフォールバックを採用。
    - リトライ・バックオフ、ログ出力、例外処理（DB 書き込みエラー時はロールバックして上位へ伝播）を実装。

- リサーチ（kabusys.research）
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近の財務を取得して PER / ROE を計算（EPS が無効な場合は None）。
    - DuckDB SQL を利用した効率的なウィンドウ集計を実装。データ不足時は None を返却する堅牢設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足時は None。
    - rank: 同順位は平均ランクとするランク付け実装（丸め処理で float の誤差を吸収）。
    - factor_summary: count/mean/std/min/max/median を計算する要約統計。
  - research パッケージ __init__ にて主要関数を再エクスポート。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。market_calendar テーブルの有無に応じて DB 値優先、未登録日は曜日ベースでフォールバック。
    - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を更新する夜間バッチ処理。バックフィル・健全性チェックを実装。
    - 最大探索日数制限や NULL 値検出での警告ログなど堅牢性対策を実施。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧を格納）。has_errors / has_quality_errors / to_dict 等のユーティリティを提供。
    - 差分取得、バックフィル、品質チェック（quality モジュール経由、重大度管理）等の設計指針を実装。
    - etl.py で ETLResult を公開再エクスポート。

- 汎用設計・運用面
  - DuckDB を主要なデータストアとして使用（すべての分析/ETL/カレンダー処理が DuckDB 接続を受け取る形）。
  - LLM 呼び出しは api_key を引数で注入可能（環境変数 OPENAI_API_KEY と併用）してテスト容易性を確保。
  - ルックアヘッドバイアス防止設計: 各モジュールで datetime.today()/date.today() を直接参照しない実装方針を採用（target_date ベースの処理）。
  - 外部依存は最小化（pandas 等を使わず標準ライブラリ + duckdb + openai を前提）。

### 変更
- なし（初回リリースのため）。

### 修正
- なし（初回リリースのため）。

### 非推奨
- なし。

### セキュリティ
- なし。

### 注意事項 / 既知の制限
- OpenAI の JSON Mode（response_format={"type":"json_object"}）を利用しているため、使用する OpenAI SDK / モデルが対応している必要があります。
- DuckDB の executemany に対して空リストを渡せない制約に配慮した実装（空チェックを挟んでいる）。
- jquants_client モジュールは別途実装を想定（calendar_update_job / ETL で呼び出すため）。
- テスト容易性のため、LLM 呼び出し箇所（_call_openai_api）をモック差し替え可能にしている。自動環境変数ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- 一部の処理はネットワーク/外部 API に依存するため、実稼働環境では適切な API キーとネットワーク設定が必要です。

---

（この CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートとして使う場合は、実装状況や公開 API の意図に合わせて適宜修正してください。）