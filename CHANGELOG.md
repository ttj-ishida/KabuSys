# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

※ バージョン番号はパッケージの `kabusys.__version__`（0.1.0）に合わせています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01
初回リリース

### Added
- パッケージ構成を追加
  - `kabusys` パッケージの公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` として定義。
  - バージョン情報 `kabusys.__version__ = "0.1.0"` を追加。

- 環境設定・ロード機能（`kabusys.config`）
  - プロジェクトルート検出機能 `_find_project_root()`：`.git` または `pyproject.toml` を基準にルートを探索（CWD に依存しない自動 .env ロード）。
  - `.env` ファイルパーサ `_parse_env_line()`：`export KEY=val`、クォート文字列（バックスラッシュエスケープ考慮）、インラインコメント処理などに対応。
  - `.env` 読み込み `_load_env_file()`：OS 環境変数を保護する `protected` オプション、上書き制御 `override` をサポート。
  - 自動ロード機能：`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による無効化が可能。
  - 設定ラッパー `Settings`：J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境（`KABUSYS_ENV`）・ログレベル検証を提供。必須環境変数未設定時に分かりやすいエラーを返す（`_require()`）。

- AI モジュール（`kabusys.ai`）
  - ニュース NLP スコアリング（`kabusys.ai.news_nlp`）
    - OpenAI（`gpt-4o-mini`）を用いた銘柄別ニュースセンチメント解析機能 `score_news(conn, target_date, api_key=None)` を実装。
    - 処理概要：ニュースのタイムウィンドウ計算（JST基準→UTC変換）、`raw_news` と `news_symbols` による銘柄別記事集約、1銘柄あたりの最大記事数・文字数制限、最大 20 銘柄/チャンクでのバッチ送信、レスポンスの厳格なバリデーション（JSON 抽出・キー/型チェック）、スコアの ±1.0 クリップ、取得済み銘柄のみを置換（DELETE → INSERT）する冪等書き込み。
    - 再試行ロジック：429/接続断/タイムアウト/5xx に対する指数バックオフリトライ（最大設定あり）。その他のエラーはスキップして継続するフェイルセーフ設計。
    - テスト容易性：OpenAI 呼び出し部分を `unittest.mock.patch` で差し替え可能に設計（`_call_openai_api` を差し替えられる）。
    - DuckDB の `executemany` に関する互換性考慮（空リストの扱いを回避）。
  - 市場レジーム判定（`kabusys.ai.regime_detector`）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（`bull`/`neutral`/`bear`）を判定する `score_regime(conn, target_date, api_key=None)` を実装。
    - マクロ記事抽出はキーワードリスト（日本・米国等）でフィルタ。記事が無い場合は LLM 呼び出しをスキップしてマクロセンチメントを 0 とするフォールバック。
    - OpenAI 呼び出しは独自実装でモジュール結合を避け、リトライ・エラーハンドリングを実装。出力は JSON モードから数値を抽出してクリップ。
    - レジーム結果は `market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）される。

- データプラットフォーム（`kabusys.data`）
  - マーケットカレンダー管理（`kabusys.data.calendar_management`）
    - 営業日判定関数群を実装：`is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`。
    - DB にカレンダーがない場合は曜日ベース（土日非営業日）でフォールバック。
    - 夜間バッチ更新ジョブ `calendar_update_job(conn, lookahead_days=...)`：J-Quants から差分取得して `market_calendar` を冪等保存。バックフィルや健全性チェックを実装（直近の訂正を取り込むための再取得・未来日チェック）。
  - ETL パイプライン（`kabusys.data.pipeline`）
    - ETL 実行結果を表す `ETLResult` dataclass を追加（取得件数、保存件数、品質チェック結果、エラー一覧等を格納）。
    - 差分更新、バックフィル、品質チェック、id_token 注入等の設計を反映（J-Quants クライアント呼び出しは `kabusys.data.jquants_client` 経由を想定）。
    - 内部ユーティリティ：テーブル存在チェック、最大日付取得等を用意。
  - ETL 型公開（`kabusys.data.etl`）：`ETLResult` を再エクスポート。

- 研究用ユーティリティ（`kabusys.research`）
  - ファクター計算（`kabusys.research.factor_research`）
    - モメンタム（`calc_momentum`）：約1/3/6ヶ月のリターン、200日移動平均乖離（データ不足時は None）。
    - ボラティリティ・流動性（`calc_volatility`）：20日 ATR（true range の正しい扱い）、ATR 比率、20日平均売買代金、出来高比率。
    - バリュー（`calc_value`）：`raw_financials` から最新財務（report_date <= target_date）を取得して PER/ROE を計算。
    - 設計方針：DuckDB を使った SQL＋Python 実装、外部 API 呼び出しなし、本番発注 API 非依存。
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算（`calc_forward_returns`）：複数ホライズンを一括で計算。入力検証（horizons <= 252）とパフォーマンス配慮あり。
    - IC（Information Coefficient）計算（`calc_ic`）：スピアマンランク相関の実装（ties の平均ランク処理あり）。有効レコード不足（<3）時は None を返す。
    - ランク変換（`rank`）：同順位は平均ランク、丸め処理で浮動小数誤差を吸収。
    - 統計サマリー（`factor_summary`）：count/mean/std/min/max/median を計算。

### Changed
- 設計上の注意点をコードレベルで明記（ドキュメンテーション的変更）
  - ルックアヘッドバイアス防止のため、各 AI / ニュース / レジーム / ETL / 研究機能で `datetime.today()` / `date.today()` を直接参照しない設計（すべて `target_date` を引数として受ける）。
  - OpenAI 呼び出し部はモジュール間でプライベート関数を共有しない設計によりテスト容易性を向上。

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- `OPENAI_API_KEY`（または関数引数 `api_key`）が未設定だと `score_news` / `score_regime` は `ValueError` を返す（明示的設計）。運用時は環境変数または引数でキーを供給してください。
- DuckDB のバージョン差異に起因する制約（例：`executemany` に空リストを渡せない）に対応する実装上のワークアラウンドを採用。
- `kabusys.data.jquants_client` といった外部クライアントの実装はこのリリースでは参照のみ（実装は別モジュール／ライブラリを想定）。ETL・カレンダー更新は該当クライアントの実装に依存します。
- 一部関数はデータ不足時に `None` を返します（ファクター値や ATR 等）。呼び出し側で `None` を扱う必要があります。
- `monitoring` モジュールはパッケージの公開対象に含まれているが、今回差分としては個別ファイルは提示されていません（実装有無は別途確認を推奨）。

### Security
- 環境変数の扱いに注意：`.env` 自動ロードはデフォルト有効。CI・テスト等で不要な自動ロードを抑制するため `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。

---

参考:
- 主な設計思想：テスト容易性、フェイルセーフ（API失敗時のスキップ/フォールバック）、冪等な DB 書き込み（DELETE→INSERT / ON CONFLICT の利用想定）、ルックアヘッドバイアス排除。