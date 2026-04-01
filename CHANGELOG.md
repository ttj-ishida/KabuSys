CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。
セマンティックバージョニングを採用しています: https://semver.org/

Unreleased
----------

（未リリースの変更があればここに記載します）

0.1.0 - 2026-04-01
------------------

初回リリース。日本株自動売買プラットフォームの基礎機能を実装しました。主な追加内容は以下の通りです。

Added
- パッケージの初期公開
  - kabusys パッケージを公開。バージョンは 0.1.0。

- 環境設定 / ロード
  - 環境変数管理モジュールを追加（kabusys.config）。
  - .env / .env.local ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサを実装（export PREFIX、クォート、エスケープ、インラインコメントの扱い、無効行スキップに対応）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / データベース / 監視 / ログ設定等をプロパティ経由で取得可能に。
  - 環境変数未設定時に分かりやすいエラーメッセージを返す _require を実装。

- AI（OpenAI）連携: ニュース NLP と レジーム判定
  - ニュースセンチメント解析モジュール（kabusys.ai.news_nlp）を追加。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、gpt-4o-mini（JSON Mode）にバッチ送信して ai_scores テーブルに書き込む。
    - バッチ処理（最大 20 銘柄 / チャンク）、記事・文字数トリム、429/タイムアウト/5xx に対する指数バックオフのリトライを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code と score の検証）を実装。スコアは ±1.0 にクリップ。
    - テスト容易性のため _call_openai_api をパッチで差し替え可能に。
    - DuckDB の executemany の空リスト制約を考慮した安全な書き込みロジック（DELETE→INSERT）を実装。

  - 市場レジーム判定モジュール（kabusys.ai.regime_detector）を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - OpenAI 呼び出し（gpt-4o-mini）に対するリトライ／エラーハンドリングを実装。API 失敗時は macro_sentiment=0.0 としてフォールバック。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - ルックアヘッドバイアス対策を設計上組み込み（date 比較は target_date より前のみを使用、datetime.today() を参照しない）。

- データプラットフォーム（DuckDB）関連
  - ETL パイプライン基盤（kabusys.data.pipeline）を追加。
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得・バックフィル・品質チェック方針を実装するための骨組みを提供。
  - カレンダー管理モジュール（kabusys.data.calendar_management）を追加。
    - market_calendar に基づく営業日判定 / 次営業日 / 前営業日 / 期間内営業日取得 / SQ 判定などのユーティリティを実装。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする堅牢なロジックを提供。
    - 夜間ジョブ calendar_update_job を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル含む）を行う。健全性チェック（過度な未来日付検出）を実装。

- リサーチ / ファクター計算
  - ファクター計算モジュール（kabusys.research.factor_research）を追加。
    - Momentum（1M/3M/6M、200 日 MA 乖離）、Volatility（20 日 ATR/ATR 比率）、Value（PER/ROE）等を DuckDB 上の SQL で計算する関数を提供。
    - データ不足時の挙動（欠損は None）を明確化。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）を追加。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、ファクター統計サマリー（factor_summary）等を提供。
    - pandas 等の外部依存を持たず標準ライブラリ + DuckDB で実装。
  - 研究用ユーティリティをまとめた __init__ を提供（再エクスポート）。

- 汎用ユーティリティ
  - data/etl の公開インターフェースとして ETLResult を再エクスポート。
  - __all__ を適切に定義して外部公開 API を整理。

Changed / Design notes
- モジュール設計上の共通方針を明文化
  - ルックアヘッドバイアスを避けるため、内部実装は datetime.today() / date.today() を直接参照しない（関数呼び出し側で target_date を明示的に与える設計）。
  - OpenAI 呼び出しや外部 API に対してはフェイルセーフ（API 失敗時はゼロスコアまたはスキップして継続）を採用。
  - DuckDB との互換性（executemany の空リスト制約など）を考慮した実装。
  - DB への書き込みは可能な限り冪等化（DELETE→INSERT など）して部分失敗時に既存データを破壊しないよう設計。

Fixed / Fallback behavior
- データ不足（例: ETF 1321 の 200 日分データが不足）時に中立値を返す（ma200_ratio = 1.0）して処理を継続するロジックを実装。
- OpenAI レスポンスの JSON パースで前後に余計なテキストが混ざるケースに対し、最外の {} を抽出して復元を試みる処理を追加（news_nlp）。
- API 呼び出しで 5xx / タイムアウト / レート制限等に対するリトライ実装を追加。リトライ上限到達時は安全にフォールバックしてログを残す。

Security
- API キーは引数で注入可能（テスト可能）かつ環境変数 OPENAI_API_KEY をデフォルトで参照する。必須キー未設定時は明確な ValueError を送出。

Notes / テスト支援
- OpenAI 呼び出し部はテスト時に差し替え（unittest.mock.patch）しやすいよう _call_openai_api を分離してあるため、ユニットテストでのモックが容易。

Breaking Changes
- 初回リリースのため既存の公開 API との後方互換性破壊に関する記載はありません。

Acknowledgements / Known limitations
- 本バージョンでは PBR や配当利回りなどの一部バリューファクターは未実装。
- DuckDB の特定バージョンに依存する挙動（リストバインド等）に対応するためコードに互換措置を入れていますが、環境により微調整が必要な場合があります。
- OpenAI との通信は外部サービス依存であり、レイテンシや API 料金に注意してください。

今後の予定（例）
- 監視 / 実行モジュールの詳細実装（execution, monitoring パッケージ）の追加
- ファクターの追加実装（PBR、配当利回り等）
- テストカバレッジ拡充と CI 設定の公開

--- 
（この CHANGELOG はコードベースからの推測に基づき作成しています。実際の変更履歴やリリース日付はリポジトリ運用方針に合わせて調整してください。）