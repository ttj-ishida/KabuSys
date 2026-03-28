CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従っています。  
リリース日付は本CHANGELOGに記載のものを参照してください。

[Unreleased]
------------

- （現状なし）

[0.1.0] - 2026-03-28
-------------------

初回リリース。日本株自動売買システム「KabuSys」の基盤機能群を実装・公開しました。
主に以下のサブパッケージ・機能を含みます。

Added
- パッケージ初期化
  - kabusys.__version__ = "0.1.0" を設定。
  - パッケージの公開APIとして data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - 環境ファイルの行パーサ実装（export 構文、クォート内のエスケープ、インラインコメント処理を考慮）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須環境変数チェック用の _require と Settings クラスを提供。
  - 以下の設定プロパティを実装：
    - J-Quants / kabuステーション / Slack / データベースパス（DUCKDB_PATH, SQLITE_PATH）/ ログレベル（LOG_LEVEL）/ 環境（KABUSYS_ENV）
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値以外は ValueError）。

- AI 関連（kabusys.ai）
  - ニュースNL P（kabusys.ai.news_nlp）
    - raw_news / news_symbols を読んで銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する score_news を実装。
    - タイムウィンドウの計算（前日15:00 JST ～ 当日08:30 JST、内部は UTC naive datetime）を calc_news_window として提供。
    - バッチ処理（チャンクサイズ 20 銘柄）、1銘柄あたり記事数上限・文字数上限（トリム）を実装。
    - API コールの再試行（429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ）と、レスポンスバリデーションを実装。
    - JSON の前後余分テキストの復元ロジックや、未知銘柄コードの無視、スコアのクリッピングを実装。
    - テスト容易性のため _call_openai_api の差し替えを想定（patch可能）。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - MA200 計算は target_date 未満のデータのみを利用しルックアヘッドバイアスを回避。
    - マクロニュース抽出、OpenAI 呼び出し、再試行、例外処理（API失敗時は macro_sentiment=0.0 で継続）を実装。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テストのため _call_openai_api の差し替えを想定。

- Data / ETL / カレンダー（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar ベースの営業日判定ユーティリティを実装：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録値を優先し、未登録日は曜日ベース（週末判定）でフォールバックする一貫したロジック。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）や健全性チェック（将来日付の上限）を導入。
    - calendar_update_job を実装し、J-Quants API から差分取得 → market_calendar に冪等保存（fetch/save は jquants_client 経由）。

  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを実装（ETL の集計結果、品質問題リスト、エラーリストを保持）。
    - 差分取得、バックフィル、品質チェックの方針に基づくユーティリティを実装（内部関数に _get_max_date 等）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- 研究 / リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（calc_momentum）：1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - ボラティリティ（calc_volatility）：20 日 ATR、ATR の比率、20 日平均売買代金、出来高比率等を計算。
    - バリュー（calc_value）：raw_financials からの EPS/ROE を使い PER/ROE を算出（最新報告日以前の最新レコードを利用）。
    - DuckDB SQL + Python で効率的に処理。データ不足時は None を返す挙動。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：複数ホライズンのリターンを一括取得する SQL 実装（horizons の検証あり）。
    - IC 計算（calc_ic）：Spearman のランク相関（ランクは同順位で平均ランク）を実装。サンプル数不足時は None。
    - ランク変換ユーティリティ（rank）。
    - ファクター統計サマリ（factor_summary）：count/mean/std/min/max/median を計算。
  - 研究 API は外部への発注や本番API呼び出しを行わない方針（DuckDB のみ参照）。

Changed
- 設計方針の明示
  - AI モジュールと研究モジュールはルックアヘッドバイアスを避けるため datetime.today()/date.today() を内部参照しない設計。
  - OpenAI 呼び出しは JSON mode を利用し、厳密な JSON レスポンスを期待する。レスポンス検証・復元ロジックを実装。
  - DuckDB のバージョン互換性（executemany に空リストを渡さないなど）に配慮した実装。

Fixed
- （初回リリースのため過去のバグ修正はなし）

Security
- OpenAI API キー・各種シークレットは環境変数で管理する想定（Settings 経由）。必須キーが未設定の場合は ValueError を送出して明示的に失敗する実装。

Notes / Migration / Usage
- OpenAI 関連
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須です。未設定時は ValueError を送出します。
  - テスト容易性のため OpenAI 呼び出し関数はモジュールローカルの _call_openai_api を patch して差し替え可能です。

- 環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意デフォルトあり: KABU_API_BASE_URL (http://localhost:18080/kabusapi), DUCKDB_PATH (data/kabusys.duckdb), SQLITE_PATH (data/monitoring.db), LOG_LEVEL (INFO), KABUSYS_ENV (development)
  - 自動.env読み込みはパッケージ起点のファイルパス探索に基づいており、配布後も CWD に依存せず動作するよう設計。

- DuckDB
  - 実装は DuckDB の SQL ウィンドウ関数を多用しています。DuckDB のバージョンや executemany の制約に合わせた防御的実装を行っています。

Acknowledgements / Design decisions
- ニュース/レジーム判定で LLM を使う部分は、API失敗時に中立スコア（0.0）へフォールバックすることでシステム全体の堅牢性を確保しています。
- DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT の利用想定）しています。
- 研究系は外部依存を避け、標準ライブラリと DuckDB のみで再現可能に設計しています。

リンク
- （将来的にリリースタグや差分へのリンクを追加してください）

注: この CHANGELOG はリポジトリ内のソースコードから推測して作成しています。実際のコミット履歴や設計書と差異がある場合があります。