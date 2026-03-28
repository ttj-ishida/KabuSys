# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルでは重大度（Added / Changed / Fixed / Deprecated / Removed / Security）で分類しています。

全般的な方針:
- ルックアヘッドバイアス回避のため、各モジュールは内部で datetime.today()/date.today() を直接参照しない設計を採用しています（引数で基準日を受け取る）。
- DuckDB を主要なローカルデータストアとして想定し、DB 操作は冪等性・部分失敗耐性を重視した実装になっています。
- OpenAI（gpt-4o-mini）を JSON mode（response_format）で使用する設計を採用し、API 呼び出しはリトライ戦略やフェイルセーフを備えています。

## [Unreleased]
- 予定:
  - ai モジュールのテスト用フック/モックを拡充してユニットテスト性を向上。
  - ETL パイプラインにより詳細な監査ログ出力を追加。
  - ai/news_nlp の出力検証（スキーマ検証）の強化とより詳細なログ。
  - jquants_client 周りのエラー分類・再試行を強化。
  - パッケージのドキュメント（Usage / Examples）追加。

---

## [0.1.0] - 2026-03-28

### Added
- プロジェクトの初期公開（kabusys 0.1.0）。
  - パッケージ構成:
    - kabusys.config: 環境変数/.env 管理（自動ロード機能・.env.local 優先度等）
    - kabusys.ai:
      - news_nlp.score_news: ニュース記事を銘柄ごとに集約して OpenAI でセンチメント解析し ai_scores テーブルへ書き込む。
      - regime_detector.score_regime: ETF(1321) の200日移動平均乖離とマクロニュースの LLM センチメントを合成して market_regime を判定・保存。
    - kabusys.research:
      - factor_research.calc_momentum / calc_volatility / calc_value: モメンタム・ボラティリティ・バリュー系ファクター計算。
      - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン計算、IC（Spearman ρ）、統計サマリーなどの研究用ユーティリティ。
    - kabusys.data:
      - calendar_management: 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job）。
      - pipeline / etl: ETL パイプライン基盤、ETLResult データクラス（kabusys.data.etl 経由で再エクスポート）。
  - __init__ によるパッケージエクスポート（data, strategy, execution, monitoring を __all__ に定義）。

- 環境設定と自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動検出して読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env パースの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - 行末コメント・インラインコメントの扱いを改善
  - .env.local は .env を上書きする動作（ただし OS 環境変数は protected として上書き回避）。

- AI / OpenAI 連携:
  - gpt-4o-mini を用いた JSON Mode 呼び出し（response_format={"type": "json_object"}）。
  - レスポンスパースの耐障害性向上（前後に余計なテキストが混ざった場合に {} を抽出して復元する処理）。
  - API 呼び出しに対するリトライと指数バックオフ（429・ネットワーク断・タイムアウト・5xx 群）。
  - API 失敗時のフェイルセーフ（news_nlp は該当チャンク・銘柄をスキップ、regime_detector は macro_sentiment=0.0 として続行）。

- データベース操作の堅牢化:
  - ai_scores / market_regime などへの書き込みは冪等性を保つ（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。
  - DuckDB の制約（executemany に空リスト不可）への対処ロジックを実装。
  - ETLResult クラスによる ETL 実行結果の構造化（品質問題の集約、has_errors / has_quality_errors ヘルパー）。

- カレンダー管理:
  - market_calendar が未取得の場合の曜日ベースのフォールバック（週末を非営業日扱い）。
  - next_trading_day / prev_trading_day / get_trading_days の実装（DB 優先、未登録日は曜日フォールバック、一貫性の保証）。
  - calendar_update_job: J-Quants から差分取得して保存する夜間ジョブ（バックフィル、健全性チェックあり）。

- リサーチ系の数値処理:
  - 各種ファクター計算は DuckDB 上の SQL ウィンドウ関数を活用して高速に処理。
  - rank() は同順位を平均ランクで処理し、丸め誤差対策を実装。
  - factor_summary は基本的な統計量（count/mean/std/min/max/median）を返す。

### Changed
- なし（初回リリースのため実装が主体）。

### Fixed
- env ファイル読み込み時のエッジケース（クォート内のエスケープ、コメント扱い、空行・コメント行スキップ）に対応。
- OpenAI レスポンスの JSON パース失敗に対してより寛容な復元処理を追加（余計な前後テキストの抽出）。
- DuckDB executemany の空リストバインドによるクラッシュを回避するガードを追加。

### Deprecated
- なし。

### Removed
- なし。

### Security
- 環境変数に機微な情報（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）を利用。
  - .env 自動ロードは OS 環境変数を上書きしない（保護）ため、システムの環境変数保護を考慮。
  - 自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。

---

注記:
- 本リリースでは外部依存として openai SDK と duckdb を想定しています。OpenAI の API 仕様や SDK の変更（例: 例外クラスやステータスコードの取り扱い）があるため、将来の SDK 変更に対する互換性対応が必要です（regime_detector では status_code を getattr で安全に取得する等の工夫あり）。
- AI による評価結果は LLM の出力に依存するため、運用では結果品質の監査（quality チェックやヒューマン確認）を推奨します。