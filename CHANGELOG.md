# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。KabuSys の基本機能を実装しました。以下の主要機能・モジュールを含みます。

### Added
- パッケージ基盤
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
  - パッケージ公開インターフェースに `data`, `strategy`, `execution`, `monitoring` を含む `__all__` を定義。

- 環境設定 / ロード
  - `kabusys.config` モジュールを追加。
    - `.env` / `.env.local` ファイルおよび OS 環境変数から設定を自動ロード（プロジェクトルートは `.git` または `pyproject.toml` を基準に探索）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - `.env` 行パーサを実装（コメント、`export` プレフィックス、シングル/ダブルクォート、エスケープ対応）。
    - 環境変数取得ユーティリティ `_require` と `Settings` クラスを提供（J-Quants トークン、kabu API、Slack、DB パス、環境判定、ログレベルなど）。
    - 許容される環境値のバリデーション（`KABUSYS_ENV`, `LOG_LEVEL`）。

- AI: ニュース NLP（センチメント）および市場レジーム検出
  - `kabusys.ai.news_nlp`
    - raw_news と news_symbols を元にニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（JST ベースの前日 15:00 〜 当日 08:30 に相当する UTC 範囲）。
    - バッチング（最大 20 銘柄 / リクエスト）、記事数・文字数トリムでトークン肥大化対策。
    - 429/ネットワーク/タイムアウト/5xx を対象にエクスポネンシャルバックオフでリトライ。API 以外の例外はスキップして継続するフェイルセーフ動作。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列形式、コード整合、数値チェック）と ±1.0 のクリップ。
    - DuckDB の制約（executemany に空リスト不可）に配慮した ai_scores テーブルへの冪等的書き込み（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し関数 `_call_openai_api` を差し替え可能（mock 対応）。
  - `kabusys.ai.regime_detector`
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロキーワードで raw_news を抽出し、OpenAI（gpt-4o-mini）で JSON 出力を期待して sentiment を取得。API 失敗時は macro_sentiment=0.0 で継続。
    - レジームスコア合成と閾値判定、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計（テスト時に差し替え可能）。

- データプラットフォーム（ETL / カレンダー）
  - `kabusys.data.pipeline` / `kabusys.data.etl`
    - ETL パイプラインの結果を表す `ETLResult` データクラスを提供（取得件数、保存件数、品質チェック結果、エラー一覧等）。
    - 差分取得、バックフィル、品質チェックの設計に基づく基本インターフェース実装（実装内で DuckDB と jquants_client を利用する設計）。
  - `kabusys.data.calendar_management`
    - JPX カレンダー管理と営業日ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が存在しない場合は曜日（平日）ベースでのフォールバックを実施。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存する処理を提供（バックフィル日数、健全性チェックあり）。
    - DB に欠損・NULL 値がある場合のフォールバックや警告ログ出力などの堅牢性確保。

- 研究（リサーチ）用ユーティリティ
  - `kabusys.research.factor_research`
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装。すべて DuckDB の prices_daily / raw_financials を参照する設計。
    - データ不足時の None 扱い、窓幅・スキャン範囲に関する設計配慮。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）および IC（Spearman の ρ）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存しない純 Python 実装で、欠損や ties の扱いを明確化。

- 内部ユーティリティ
  - `kabusys.data.__init__` などの名前空間整備、etl の ETLResult 再エクスポート等。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動ロード時に既存 OS 環境を保護する仕組み（protected set）を実装。`.env.local` は override=True で上書きするが、OS 環境変数は保護される。
- OpenAI API キーは明示的に引数で渡すことが可能。未指定時は環境変数 `OPENAI_API_KEY` を参照。

### Notes / Design decisions / Known behavior
- ルックアヘッドバイアス防止:
  - すべての分析関数（ニュース窓、MA 計算、ETL、AI スコアリング等）は内部で datetime.today() / date.today() を直接参照せず、外部から与えられた target_date を基準に動作します。
- フェイルセーフ設計:
  - OpenAI API が利用できない場合、ニュース系の関数は例外で処理を止めず（多くは 0.0 や空の結果にフォールバック）ログ出力して継続する設計。
- DuckDB 互換性:
  - executemany の空リストバインド制約など、現状の DuckDB の挙動を考慮した実装を行っています。
- テスト支援:
  - OpenAI 呼び出し部はモック差し替え可能（内部関数を patch できる）に実装してあり、ユニットテストでの外部 API 依存を避けられます。
- デフォルト値:
  - DB ファイルパスなどの既定値は `data/kabusys.duckdb` / `data/monitoring.db` 等を使用。
- 依存:
  - DuckDB、openai（OpenAI SDK）等の外部ライブラリに依存します。

---

今後の予定（非網羅）:
- strategy / execution / monitoring の具象実装（現状は名前空間のみ公開）。
- より細かい品質チェックルールの追加、ETL ジョブの自動化サポート。
- テストカバレッジの拡充と CICD 用のワークフロー整備。

--------------------------------------------------------------------------------
参照: 本 CHANGELOG はソースコードの内容から推測して作成しています。動作・仕様の詳細は各モジュールの docstring を参照してください。