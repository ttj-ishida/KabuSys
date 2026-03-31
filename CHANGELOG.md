# Changelog

すべての重要な変更点をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
このリポジトリのコード状態から機能・設計意図を推測して記載しています。

全般:
- 依存: duckdb, openai (OpenAI Python SDK) などを前提とした設計。
- 設定は環境変数 / .env ファイルで管理（自動ロードあり、無効化フラグあり）。
- 日付・時刻扱いにおいてルックアヘッドバイアスを避ける設計が各モジュールで共通して採用されています（内部で datetime.today() / date.today() を参照しない設計方針が明示）。

## [Unreleased]
- （現在のリポジトリ状態が初回リリースに相当するため未リリースの変更はありません。）

## [0.1.0] - 2026-03-31
初回リリース（推定）。以下の主要な機能群と設計上の注記を含みます。

Added
- パッケージ基盤
  - kabusys パッケージのエントリポイントを追加（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring（monitoring は __all__ に存在するが実装は今回のコードと別ファイルと想定）。
  - バージョン: 0.1.0 を定義。

- 設定管理（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。OS 環境変数優先の読み込み順を採用。
  - エクスポート形式（export KEY=val）、クォート文字列、インラインコメントの扱い、エスケープ解釈に対応したパーサを実装。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、アプリ固有の設定プロパティを公開（J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境・ログレベル判定など）。
  - 設定値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）や必須 env の未設定時に ValueError を送出する _require を実装。

- AI 関連（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチで問い合わせて銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む。
    - バッチサイズ、記事数・文字数上限、タイムウィンドウ（JST 基準で前日 15:00 ～ 当日 08:30 を UTC に変換）などが定義されている。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフリトライ、JSON 応答の堅牢なパース（前後余計テキスト復元）とバリデーションを実装。
    - 部分失敗を許容するように、書き込みは対象コードのみ DELETE → INSERT の形で冪等に行う（DuckDB executemany の空リスト問題への対応あり）。
    - テスト容易性のため api_key 注入と _call_openai_api の差し替えを想定。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を market_regime テーブルへ冪等書き込みする。
    - マクロセンチメントは raw_news からマクロキーワードで抽出したタイトルを gpt-4o-mini に送り JSON で取得。API 障害時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - API 呼び出しに対してもリトライ方針・エラーハンドリングを実装。
    - ルックアヘッド防止のため、prices_daily クエリは target_date 未満のデータのみ参照する設計。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー保存・問合せ用ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得のときは曜日ベース（土日休）でフォールバック。
    - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得して market_calendar を冪等保存（fetch + save）。
    - 最大探索日数やバックフィル日数、健全性チェックなどの安全措置を実装。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラス（target_date, fetched/saved counts, quality_issues, errors）を公開。
    - 差分更新、backfill、品質チェック（quality モジュール想定）、id_token 注入などを想定した設計。
    - _table_exists 等の DB ユーティリティを実装。
  - jquants_client との連携はモジュール分離（fetch/save を外部で提供）を想定。

- リサーチ系（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials のみ参照する純粋な計算モジュール。
    - 200日 MA、1M/3M/6M リターン、20日 ATR、20日平均売買代金、出来高比などを計算。データ不足時には None を返す形でロバストに動作。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関による IC）、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB SQL の組合せで実装。

Changed
- （初回リリースのため該当なし。ただし設計メモとして以下の動作を明記）
  - 各モジュールは「ルックアヘッドバイアス防止」を明確に守る（内部で現在日時を参照せず、target_date を明示的に受け取る）。
  - OpenAI 呼び出しはモジュール間でプライベート関数を共有せず、各モジュールで独立実装（テスト時に差し替え可能）。

Fixed
- 初期実装段階で堅牢性を重視した実装を行っている点を明記:
  - .env パーサがクォートやエスケープ、export プレフィックス、コメントを正しく扱うよう実装。
  - news_nlp の JSON パースは余剰テキストを含むケースに対して最外側の {} を抽出して復元するなど、実運用での不正確な返却を想定している。
  - OpenAI の API エラー時はフェイルセーフ（0.0 を返す、スキップして継続）とし、致命的な例外は上位へ伝播するが一般的な API 障害で処理全体が停止しないよう配慮。
  - DuckDB の executemany に空リストが渡せない既知の制約に対するガードを実装（空チェック）。

Security
- 必須環境変数（例: OPENAI_API_KEY, SLACK_BOT_TOKEN 等）が未設定の場合は ValueError を送出する明示的なチェックを導入。
- .env 自動ロードは任意で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

Notes / Migration
- OpenAI 関連関数はテスト用に差し替え可能（unittest.mock.patch を利用して _call_openai_api を置き換えられる）。
- DuckDB の型やバージョンによっては配列バインドや executemany の挙動が変わるため、ai 書き込みや ETL の executemany 部分は互換性に注意。
- target_date を明示的に渡す設計のため、運用ジョブでは必ず日次バッチ毎に正しい target_date を供給すること。

Acknowledgements / Contributors
- この CHANGELOG はソースコードの内容から推測して作成しています。実際の履歴（コミットログ）と差異がある場合があります。

----- 
変更点の補足や別バージョンの履歴（過去のコミットに基づく正確な CHANGELOG）を希望される場合は、コミットログやリリースノートの情報を提供してください。