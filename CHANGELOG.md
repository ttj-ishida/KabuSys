KEEP A CHANGELOG に準拠した形式で、コードベースから推測して 0.1.0 リリース用の CHANGELOG.md（日本語）を作成しました。

CHANGELOG.md
=============

すべての注目すべき変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
フォーマット: バージョン / 日付 / Added, Changed, Fixed, その他

## [0.1.0] - 2026-03-31
初回公開リリース — 日本株自動売買 / データ処理 / 研究・分析基盤のコア機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージの基本 __init__ を追加。バージョンは 0.1.0。
  - パッケージ公開モジュール一覧に data, strategy, execution, monitoring を設定。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - .env パーサを実装: コメント行, export プレフィックス, シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど多数のケースに対応。
  - 環境変数の必須チェック用 _require と Settings クラスを提供。各種設定プロパティ（J-Quants、kabu API、Slack、DB パス、監視閾値、実行環境判定、ログレベル）をカプセル化。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）を実装。

- データ基盤 (kabusys.data)
  - カレンダー管理モジュールを実装（market_calendar 管理、営業日判定、next/prev/get_trading_days、SQ 日判定、夜間バッチ calendar_update_job）。
    - DB にカレンダー情報がない場合は曜日ベースでフォールバック。
    - カレンダー取得のバックフィル、健全性チェック（将来日付の異常検出）を実装。
  - ETL フレームワークの骨組みを実装（pipeline.ETLResult データクラス、etl モジュールの公開インターフェース）。
    - 差分更新・バックフィル・品質チェック方針をドキュメント化。

- 研究・解析 (kabusys.research)
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を使った PER / ROE の算出（EPS が 0/欠損時は None）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得（デフォルト: 1,5,21 日）。
    - calc_ic: スピアマンランク相関 (IC) を計算するユーティリティ。
    - rank, factor_summary: ランク付け / ファクター統計サマリを提供。
  - 研究用 API は DuckDB 接続を受け取り prices_daily / raw_financials のみを参照する設計（本番発注 API には接続しない）。

- AI / NLP 機能 (kabusys.ai)
  - news_nlp モジュール: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）により銘柄ごとのセンチメント ai_score を生成する score_news を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC 変換）を実装。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄）、1 銘柄あたりの最大記事数・文字数トリム、JSON Mode による厳密 JSON 出力期待を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、コード・スコア検証）を実装。
    - DuckDB の executemany 空リスト制約に対応（空パラメータを渡さないガード）。
  - regime_detector モジュール: ETF 1321 の 200 日 MA 乖離 (重み 70%) とマクロニュース LLM センチメント (重み 30%) を合成して日次で market_regime に書き込む score_regime を実装。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを排除。
    - マクロキーワードで raw_news をフィルタして LLM に送信、出力 JSON を解析して macro_sentiment を得る。
    - レジーム合成、閾値に応じたラベル付け（bull / neutral / bear）と冪等的 DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - OpenAI 呼び出しはテスト時に差し替え可能（_call_openai_api を patch 可能）な実装。

### Changed
- （初回リリースにつき大きな変更履歴なし。各モジュールに設計方針・安全策（ルックアヘッド回避、フェイルセーフ）を明記。）

### Fixed / Robustness
- OpenAI API 呼び出しに対する堅牢性強化:
  - RateLimitError、APIConnectionError、APITimeoutError、5xx 系エラーに対する指数バックオフとリトライ実装。
  - API 失敗やレスポンスパース失敗時は例外を上位に伝播させずフォールバック値（macro_sentiment=0.0、空スコア）で継続する設計。ログで警告を出力。
  - APIError（非 5xx）やレスポンスの JSON 構文エラー等の扱いを分岐して安全に処理。
- DuckDB の互換性対応:
  - executemany に空リストを渡すと失敗する問題に対して事前チェックを追加。
  - テーブル存在チェックや日付値変換ユーティリティを整備。
- DB 書き込みの冪等性とトランザクションハンドリング:
  - market_regime / ai_scores の更新は DELETE→INSERT の冪等パターンを採用し、例外発生時は ROLLBACK を試みる。ROLLBACK 失敗時のログ出力を追加。
- 環境ファイルパースの堅牢化:
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントなどのケースに対応。
  - 読み込みできない .env ファイルは警告ログを出力して安全に無視。

### Security
- 環境変数の保護: .env 自動読み込み時に既存の OS 環境変数を保護（.env.local による上書きは可能だが、OS 環境変数は protected として扱う）。

### Notes / Implementation details
- ルックアヘッドバイアス防止: AI / 指標計算関数は内部で datetime.today()/date.today() を直接参照せず、必ず target_date を引数で受け取る設計。
- テスト容易性: OpenAI 呼び出し箇所はモック差し替えしやすいように関数を分割（_call_openai_api を patch 可能）。
- DuckDB をメインの分析 DB として想定。外部 API（J-Quants、OpenAI）はクライアント抽象化を用いて差し替え／モックが可能。
- 未実装 / 今後の拡張点（ドキュメントに明記）:
  - research の一部（PBR・配当利回り等）は未実装。
  - strategy / execution / monitoring の具象実装は本スナップショットでは見当たらないため、別途実装予定。

---

注: 本 CHANGELOG は提示されたソースコードから機能・設計意図を推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース管理ポリシーに合わせて調整してください。