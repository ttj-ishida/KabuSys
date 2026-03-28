# KEEP A CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-28
初回公開リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パッケージ公開用のモジュールエクスポートを定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルと環境変数からの設定ロード機能を実装。プロジェクトルートの自動探索は .git または pyproject.toml を基準に行うため、CWD に依存しない。
  - .env と .env.local の読み込み順序を実装（OS環境変数 > .env.local > .env）。.env.local は上書き（override）する挙動。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能（テスト用途）。
  - .env のパースは export 形式、クォート内のエスケープ、インラインコメント扱い等に対応。
  - Settings クラスを提供し、J-Quants、kabuステーション、Slack、データベースパス、実行環境（development/paper_trading/live）などのプロパティを公開。値の妥当性検証（env 値、ログレベルなど）を行う。
  - 必須環境変数未設定時に ValueError を発生させる _require ヘルパーを実装。

- AI（自然言語処理）機能 (kabusys.ai)
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini、JSON Mode）にバッチで問い合わせてセンチメント（ai_score）を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で計算。
    - バッチサイズ、記事数上限、文字数上限、リトライ（指数バックオフ）などを設定し、429/ネットワーク/タイムアウト/5xx をリトライ対象とする堅牢な実装。
    - レスポンスのバリデーションとスコアクリッピング（±1.0）、および DuckDB への冪等書き込み（DELETE → INSERT）を実装。
    - テスト容易性のため _call_openai_api を patch で置き換え可能に設計。
  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp を用いたマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - calc_ma200_ratio、マクロキーワードによる記事抽出、OpenAI への問い合わせ、スコア合成、そして market_regime テーブルへの冪等書き込みを実装。
    - OpenAI 呼び出しは独立実装とし、API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - 設計上ルックアヘッドバイアスを防止（datetime.today() 等を参照しない）する実装方針を明示。

- データ処理・ETL・カレンダー (kabusys.data)
  - calendar_management
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得して market_calendar を冪等に保存。
    - 営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（平日）でフォールバックする一貫した動作を実装。探索範囲の上限（_MAX_SEARCH_DAYS）で無限ループを回避。
    - バックフィル期間や健全性チェック（過度に未来の日付を検出した場合のスキップ）を実装。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を etl モジュールで再エクスポート）。
    - ETL の設計に基づいた差分取得・保存・品質チェックワークフローを実装するためのユーティリティを実装。保存は jquants_client の save_* 系関数を利用して冪等性を確保。
    - バックフィルやカレンダー先読み等のパラメータ化により後出し修正を吸収する設計。
    - 品質チェックはエラーを収集して呼び出し側に判断を委ねる（Fail-Fast ではない）。
    - DuckDB をメインのストレージとして使用し、テーブル存在チェックや最大日付取得ユーティリティを提供。

- リサーチ機能 (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）などのファクター計算関数を実装（prices_daily / raw_financials に依存）。
    - データ不足時の None 処理、結果を (date, code) をキーとした辞書のリストで返す仕様。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（スピアマンランク相関）計算、ランク変換ユーティリティ、ファクター統計サマリーを提供。
    - 外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB で完結する実装。
    - rank は同順位を平均ランクで扱うなど統計上の注意を取り入れた実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

### Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス防止:
  - AI スコアリングおよびレジーム判定は内部で現在時刻（datetime.today() / date.today()）を直接参照しない設計。呼び出し側が対象日（target_date）を明示的に渡すことで将来情報の混入を防止。
- フェイルセーフ:
  - OpenAI API 呼び出しの失敗やパースエラーは基本的に例外を上位に伝播させず、0.0 やスキップで継続する箇所を多く実装（運用時の停止を避ける方針）。
- 冪等性と部分失敗耐性:
  - DuckDB への書き込みは DELETE → INSERT の形で冪等に更新。ai_scores や market_regime は書き込み対象コードを限定することで部分失敗時に既存データを保護。
- テスト容易性:
  - OpenAI 呼び出し関数（_call_openai_api）を patch で差し替えられるようにしてあり、ユニットテストでの疑似応答注入を想定。
- 外部依存軽減:
  - research モジュールは pandas 等に依存せず、標準ライブラリのみで統計計算を実施。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの具現化と実運用連携（kabuステーション発注・Slack通知等）
- jquants_client の具体実装と ETL の運用化（スケジューリング・監査ログ）
- テストカバレッジ拡充、CI ワークフロー整備

（以上）