# Changelog

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※日付はリリース想定日で記載しています（コードベースの内容から推測）。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムのコアライブラリを提供します。主要なサブモジュール（設定管理、データ ETL / カレンダー管理、研究用ファクター計算、AI ベースのニュース分析と市場レジーム判定）を実装しました。

### Added
- パッケージ基礎
  - パッケージバージョン定義: kabusys.__version__ = "0.1.0"
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルと環境変数から設定を自動ロードする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理をサポート。
  - 環境変数取得用 Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants, kabuステーション, Slack, DB パス, 環境種別 (development / paper_trading / live), ログレベル等のプロパティを提供。
    - 必須キー未設定時は ValueError を発生させる _require を実装。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約して OpenAI (gpt-4o-mini) に送信し、センチメント (ai_scores テーブルへ書き込み) を計算。
    - 時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたり最大記事数・文字数トリム (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)。
    - JSON Mode を用いたレスポンスパースと厳格なバリデーション (_validate_and_extract)。
    - 429／ネットワーク断／タイムアウト／5xx に対する指数バックオフのリトライ実装。
    - API 失敗やパース失敗はフェイルセーフでスキップ（例外を投げず処理継続）。
    - スコアは ±1.0 にクリップ。
    - 書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT。DuckDB executemany の空リスト回避）。
    - 公開関数: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news / market_regime テーブルを使用し、結果を market_regime に冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロキーワードによる記事抽出と OpenAI による JSON 出力パース。
    - API エラー時は macro_sentiment = 0.0 として継続するフェイルセーフ。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データプラットフォーム (`kabusys.data`)
  - ETL パイプライン基盤 (`kabusys.data.pipeline`)
    - ETLResult データクラスで ETL の実行結果（取得数・保存数・品質問題・エラー）を表現。
    - 差分更新、バックフィル、品質チェックを想定した設計（jquants_client と quality モジュールを利用する想定）。
  - ETLResult の再エクスポート (`kabusys.data.etl`)
  - カレンダー管理 (`kabusys.data.calendar_management`)
    - market_calendar を用いた営業日判定と夜間更新ジョブ (calendar_update_job) を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar 未取得時は曜日ベースでフォールバック（土日を休日扱い）。
    - DB 優先だが未登録日は曜日フォールバックで一貫性を保つ設計。
    - calendar_update_job: J-Quants クライアント経由で差分取得・冪等保存、バックフィルと健全性チェックを実装。

- リサーチ / ファクター (`kabusys.research`)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率 (ma200_dev) を計算。
    - calc_volatility: 20日 ATR、ATR 比率、平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER / ROE を計算（EPS が 0/欠損の時は None）。
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照（読み取り専用・発注等の副作用なし）。
  - feature_exploration モジュール
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算（欠損値除外、サンプル数閾値あり）。
    - rank: 平均ランク（同順位は平均ランク）を計算するユーティリティ。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を返す。
  - research パッケージの __all__ に主要関数を公開。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- 環境変数の自動ロードは OS 環境変数の上書きを防ぐ保護機構（protected set）を導入。
- 必須環境変数未設定時に即座に ValueError を出すことで、不正な実行を防止。

### Notes / Design decisions（重要）
- ルックアヘッドバイアス回避
  - 全ての処理で datetime.today() / date.today() を参照しない設計思想を徹底（API 呼び出し時には明示的に target_date を受け取る）。
  - DB クエリは target_date 未満／以前 等の排他条件を正しく扱うように設計。
- フェイルセーフ性
  - 外部 API（OpenAI / J-Quants）での失敗時は可能な限り処理を継続し、致命的エラーは上位で判断できるようにエラー情報を収集する（ETLResult.errors 等）。
  - OpenAI 呼び出しはリトライ・バックオフを実装し、最終的に失敗した場合は対象のみスキップ。
- DB 書き込みの冪等性
  - market_regime / ai_scores 等への書き込みは既存レコードを対象に DELETE → INSERT の形で置換し、部分失敗時に他データを保護する設計。
- DuckDB 互換性
  - executemany に空リストを渡さない等、DuckDB の既知の制約に配慮した実装。

## 開発上の注意 / 今後の予定（推測）
- strategy・execution・monitoring モジュールの実装（現在はパッケージエクスポート名として存在）。
- テスト用フックの充実（OpenAI 呼び出しのモックや KABUSYS_DISABLE_AUTO_ENV_LOAD の利用）。
- エラー・品質検出の UI/エクスポート（監査ログや Slack 通知等）実装。

---

（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートとして使用する場合は、必要に応じて担当者による確認・追補をお願いします。）