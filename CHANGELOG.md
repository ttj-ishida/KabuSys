# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  

- リリース日付はコードベースから推測して記載しています（参照日: 2026-03-29）。
- このファイルはコード内容からの推測に基づく初期リリース向けの変更履歴です。

## [Unreleased]
- （今後の変更/修正をここに記載）

## [0.1.0] - 2026-03-29

### Added
- 基本パッケージ構成を追加
  - パッケージ名: `kabusys`
  - サブモジュールの公開: `data`, `strategy`, `execution`, `monitoring`（`__all__` にて公開）

- 環境設定/ローダー
  - `.env` / `.env.local` をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを追加。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサーは `export KEY=val` 形式、クォートされた値、インラインコメント（スペース／タブ前の `#`）等に対応。
  - `Settings` クラスを実装し、環境変数から以下の設定プロパティを提供:
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB/SQLite）/実行環境（development/paper_trading/live）/ログレベル
  - 必須環境変数が未設定の場合は `ValueError` を投げる `_require` ユーティリティを実装。

- AI 関連（OpenAI を用いたニュース解析・レジーム判定）
  - `kabusys.ai.news_nlp`:
    - score_news(conn, target_date, api_key=None): raw_news/news_symbols を集約し、銘柄ごとのセンチメントを OpenAI（gpt-4o-mini）で評価して `ai_scores` テーブルへ書き込む。
    - ニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する `calc_news_window` を実装。
    - バッチ（最大 20 銘柄）での API 送信、1 銘柄あたりの記事数／文字数上限、JSON mode を想定したレスポンス検証、スコアの ±1.0 クリップなどを実装。
    - API 呼び出し失敗時はエクスポネンシャルバックオフでリトライ（429/ネットワーク断/タイムアウト/5xx）。それ以外はスキップして処理継続するフェイルセーフ設計。
    - テストのために `_call_openai_api` を patch 可能にしている。
    - DuckDB の制約（executemany に空リスト不可）を考慮して、部分置換（DELETE → INSERT）で冪等書き込みを実現。
  - `kabusys.ai.regime_detector`:
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して `market_regime` テーブルへ書き込む。
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス回避）。
    - マクロ記事が無い場合/API 失敗時は `macro_sentiment=0.0` を採用するフェイルセーフ。
    - OpenAI 呼び出しは独立した内部実装でモジュール結合を避けている。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と失敗時のROLLBACK処理を実装。

- データプラットフォーム / カレンダー・ETL
  - `kabusys.data.calendar_management`:
    - JPX 市場カレンダーを管理する関数群: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - DB（`market_calendar`）の登録値を優先し、未登録日は曜日ベース（平日）でのフォールバックを行う一貫した判定ロジックを実装。
    - カレンダー更新バッチ `calendar_update_job` を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - `kabusys.data.pipeline` / `kabusys.data.etl`:
    - ETL のための `ETLResult` データクラスを実装（取得数・保存数・品質問題・エラー一覧などを保持）。
    - 差分更新、バックフィル、品質チェック（`quality` モジュール連携）、jquants_client 経由の冪等保存を念頭に置いた設計。
    - `ETLResult.to_dict()` により品質問題をシリアライズ可能。

- リサーチ・ファクター計算
  - `kabusys.research.factor_research`:
    - `calc_momentum(conn, target_date)`: 1M/3M/6M リターン、200 日 MA 偏差（ma200_dev）を計算。
    - `calc_volatility(conn, target_date)`: 20 日 ATR、相対 ATR（atr_pct）、20 日平均出来高/売買代金、出来高比率などを計算。
    - `calc_value(conn, target_date)`: raw_financials から最新財務を結合して PER / ROE を計算（EPS 不在/0 は None）。
    - いずれも DuckDB の SQL ウィンドウ関数を用いて効率的に集計。
  - `kabusys.research.feature_exploration`:
    - `calc_forward_returns(conn, target_date, horizons=None)`: 将来リターン（複数ホライズン）を一度のクエリで取得。
    - `calc_ic(...)`: スピアマンランク相関（IC）を実装（値が不正・不足時は None を返す）。
    - `rank(values)`: 同順位は平均ランクで処理（丸め処理により ties 判定の安定化）。
    - `factor_summary(records, columns)`: count/mean/std/min/max/median の基本統計量計算。
  - `kabusys.research.__init__` から主要関数を再エクスポート。

- その他
  - DuckDB を前提とした分析ワークフロー（すべての分析・ETL関数が DuckDB 接続を受け取る設計）。
  - ルックアヘッドバイアスを避けるため、コード内で datetime.today()/date.today() を参照しない設計方針を各所に反映。
  - ロギングと詳細な警告メッセージを多数追加（データ不足・APIエラー・ROLLBACK失敗等のトラブルシュートに寄与）。
  - テスト容易性のため一部内部関数は patch/mocking を想定して実装（例: OpenAI 呼び出しのラッパー）。

### Changed
- （初版リリースのため履歴なし）

### Fixed
- API 呼び出し周りの堅牢性強化
  - OpenAI の RateLimit/接続/タイムアウト/5xx に対するリトライ（指数バックオフ）を導入。
  - 不正な JSON レスポンスに対する復元ロジック（文字列から最外の {} を抽出して再パース）を追加し、パース失敗時はスキップして処理継続する設計に。
  - DB 書き込みはトランザクションで行い、例外時は ROLLBACK を試行、さらに ROLLBACK 失敗時は警告ログを残す実装。

### Removed
- （初版リリースのため履歴なし）

### Deprecated
- （初版リリースのため履歴なし）

### Security
- OpenAI API キーや各種トークンは環境変数経由で取得する設計。未設定時は明示的なエラーを発生させる（運用上の注意）。
- .env 読み込みはデフォルトで有効だが、テストや安全性のために `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。

---

## 既知の制限 / 注意点（コードから推測）
- OpenAI API（gpt-4o-mini）への依存があるため、APIキーの管理とコストに注意が必要。
- `calc_value` は現時点で PBR や配当利回り等は未実装。
- DuckDB バージョンや SQL バインドの差異により executemany の挙動が環境依存になる可能性があるため、空リスト処理等で互換性対策を行っている。
- 一部の関数はデータ不足時に None を返す（十分なヒストリカルデータが必要）。
- .env の自動ロードはプロジェクトルート検出に基づくため、パッケージ配布後の運用では CWD ではなく __file__ を起点に探索する実装になっている点に留意。

---

必要に応じてこの CHANGELOG を元にリリースノートやリリース手順（パッケージ版、PyPI公開、ドキュメント更新）を作成できます。追加で出力フォーマット（英語版、GitHub リリース用テンプレート等）が必要であれば教えてください。