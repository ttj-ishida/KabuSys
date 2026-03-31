CHANGELOG
=========

すべての注目すべき変更はこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回リリース。パッケージ名: kabusys（バージョン 0.1.0）。
- パッケージ公開 API:
  - kabusys.__all__ により data, strategy, execution, monitoring を公開。
  - kabusys.data.etl で ETLResult を再エクスポート。
  - kabusys.ai でニュースNLP 機能 score_news を公開。
  - kabusys.research で各種ファクター・探索ユーティリティを公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- 環境設定 / ロード
  - kabusys.config: .env ファイルまたは環境変数から設定を読み込む仕組みを実装。
  - 自動ロードの探索はパッケージ内 file を起点に .git または pyproject.toml を基準にプロジェクトルートを特定（CWD 非依存）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサは export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行中コメントの扱い等に対応。未設定必須項目取得時は ValueError を送出。
  - 設定クラス Settings を提供し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル 等のプロパティを取得可能。env/log_level のバリデーション実装。

- データ基盤（DuckDB ベース）
  - kabusys.data.pipeline: ETLResult データクラスを実装（品質チェック情報・エラー集約を含む）。
  - 差分取得・バックフィル・カレンダー先読み等を想定した ETL 設計方針を実装。
  - DuckDB テーブル存在チェック・最大日付取得ユーティリティを実装。

- マーケットカレンダー管理
  - kabusys.data.calendar_management: market_calendar を基にした営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB 未取得時は曜日（土日）ベースのフォールバック。
    - 最大探索日数上限・バックフィル・健全性チェックを実装。
  - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新する夜間ジョブを実装（バックフィルと健全性チェック含む）。

- 研究（Research）モジュール
  - kabusys.research.factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL とウィンドウ関数を活用し、営業日ベースのラグ/移動平均を計算。
    - データ不足時は None を返す設計（安全性重視）。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、rank/統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を使わず標準ライブラリで実装。

- AI（OpenAI）関連
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON mode で一括評価し ai_scores テーブルへ書き込むフローを実装（score_news）。
    - タイムウィンドウは JST 前日 15:00 ～ 当日 08:30 を UTC に変換して判定（calc_news_window）。
    - バッチサイズ、記事数・文字数トリム、JSON レスポンス検証、スコアクリッピング（±1.0）、部分成功時の置換（DELETE → INSERT）などの安全策を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時はスキップして継続（フェイルセーフ）。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する関数 score_regime を実装。
    - prices_daily / raw_news / market_regime を参照し、計算結果を冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しは専用ヘルパーを持ち、リトライ・例外ハンドリング・フォールバックを備える。API 未設定時は ValueError。
  - 共通設計方針として、datetime.today()/date.today() を用いずルックアヘッドバイアスを防止する実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- API キー取得方法は引数優先で環境変数をフォールバックする方式を採用（テスト時の注入が容易）。

注意 / 実装上のポイント
- 多くの DB 書き込みはトランザクションで保護され、例外発生時は ROLLBACK を試行。ROLLBACK に失敗した場合は警告ログを出力して上位へ例外を伝播。
- DuckDB executemany の仕様（空リスト不可）に配慮した実装を行っている。
- OpenAI への呼び出しは JSON mode を期待しているが、稀に前後に余計なテキストが挿入されるケースを考慮してパース復元ロジックを含む。
- .env パーサは多くのシェル形式に対応。保護された OS 環境変数を上書きしない仕組みを実装。

今後の予定（例）
- strategy / execution / monitoring の具体的実装（現時点ではパッケージ公開名として存在）。
- テストカバレッジ拡充、CI ワークフロー追加。
- OpenAI 呼び出しの抽象化・モック容易性向上やロギングの詳細化。

-----