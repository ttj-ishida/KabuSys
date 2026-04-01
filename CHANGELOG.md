# Changelog

すべての変更は Keep a Changelog に準拠して記載しています。  
このプロジェクトの初期リリースの内容を、コードベースから推測してまとめています。

- リリース日: 2026-04-01
- バージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョン情報と主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする機能を実装。OS 環境変数の保護、.env.local による上書き順序、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env のパース強化：export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、無効行スキップなどに対応。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）など主要設定をプロパティとして提供。必須値が未設定の場合は明示的に ValueError を発生させるバリデーションを実装。
  - ログレベルと環境の検証（許容値チェック）を実装。

- AI（自然言語処理）モジュール（src/kabusys/ai/）
  - news_nlp.score_news: ニュース記事を集約して OpenAI（gpt-4o-mini）でセンチメント解析し、ai_scores テーブルへ書き込む処理を実装。
    - 前日 15:00 JST 〜 当日 08:30 JST のウィンドウ計算（UTC 変換）を実装（calc_news_window）。
    - 銘柄ごとに記事を集約し、トリミング（記事数上限・文字数上限）してバッチ（最大20銘柄）で API 呼び出し。
    - JSON Mode を利用した出力のバリデーション、スコアの ±1.0 クリップ、部分失敗時の DB 置換戦略（対象コードのみ DELETE → INSERT）など堅牢な書き込みを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによる再試行を実装。テストのために _call_openai_api を patch できる設計。
    - API 応答パース失敗やバリデーション失敗時はスキップしてフェイルセーフに継続する設計。

  - regime_detector.score_regime: ETF（1321）の 200 日移動平均乖離とマクロニュースの LLM センチメントを組み合わせて市場レジーム（bull/neutral/bear）を日次判定し、market_regime テーブルへ冪等的に書き込む処理を実装。
    - ma200_ratio の計算（target_date より前のデータのみ使用してルックアヘッドを防止）。データ不足時のフォールバック（中立 1.0）と WARNING ログ。
    - マクロニュース抽出（マクロキーワードでフィルタ、最大記事数制限）。
    - OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価。429/ネットワーク/タイムアウト/5xx に対する再試行実装、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - レジームスコア合成（MA 重み 70%、マクロ重み 30%、スコアクリップ）、閾値に基づくラベル付け、DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- リサーチ（研究）モジュール（src/kabusys/research/）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を prices_daily から計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播制御など堅牢な集計ロジック。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS 無しや 0 の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）で将来リターンを計算。horizons の検証と一度のクエリで複数ホライズン取得する実装。
    - calc_ic: ファクターと将来リターンのランク相関（Spearman ρ）を計算。サンプル不足時に None を返す。
    - rank: 同順位は平均ランクにする実装（丸めで ties を検出）。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
  - research パッケージ __init__ で主要関数を公開。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）用ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の営業日判定 API を提供。DB にデータがあれば DB 値優先、未登録日は曜日ベースでフォールバックする一貫したロジックを採用。
    - calendar_update_job による夜間バッチ更新（J-Quants から差分取得、バックフィル、健全性チェック、save_market_calendar 呼び出し）を実装。
    - 最大探索日数やバックフィル日数など安全ガードを実装。

  - pipeline / etl:
    - ETLResult データクラスを実装（src/kabusys/data/pipeline.py）し、ETL 処理の取得数・保存数・品質問題・エラー概要を保持・辞書化する機能を提供。
    - src/kabusys/data/etl.py で ETLResult を再エクスポートし、API を簡潔にした。

  - jquants_client / quality など外部クライアントに依存するコールを想定した差分取得・保存・品質チェックの骨格を実装（pipeline モジュールの設計に反映）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY を参照する設計。未設定時は明示エラーを発生させることで誤動作を防止。

### Notes / Implementation details（設計上の重要点）
- ルックアヘッドバイアス対策として、すべての時系列解析関数は date.today()/datetime.today() を内部的に参照せず、外部から与えられる target_date に依存する形で実装されています。
- OpenAI 呼び出し周りはテストしやすいように内部 _call_openai_api をパッチ可能にしており、unit test 用の差替えを想定した設計になっています。
- DuckDB への書き込みは冪等性を意識（対象レコードを限定して DELETE → INSERT）しており、部分失敗時に既存データを不必要に消さないよう配慮しています。
- API 呼び出しの一時的エラー（429 / ネットワーク / タイムアウト / 5xx）は指数バックオフでリトライし、長期的な失敗はフォールバック値（例: macro_sentiment=0.0）で継続するフェイルセーフ設計です。

---

以上がコードベースから推測される初期リリース（0.1.0）の CHANGELOG です。必要であれば、各モジュールごとにより詳細な変更点（関数シグネチャ、戻り値仕様、例外挙動など）を追加します。