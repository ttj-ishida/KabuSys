# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従い、後方互換性・設計上の注意点などを明記しています。

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。主な追加点と設計上の重要な振る舞い・安全策を以下にまとめます。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: `src/kabusys/__init__.py` にバージョン `0.1.0` と公開モジュール一覧を追加。
  - メインモジュール群を公開: data, research, ai, execution, monitoring, strategy 等の構成を想定したエクスポート（`__all__`）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルと環境変数を統一的に読み込む設定モジュールを追加。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を起点にルートを探索して自動で .env を読み込む処理を実装（CWD に依存しない）。
  - .env 自動ロードの優先度:
    - OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env 行パーサー: `export KEY=val`、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを正しく処理。
  - 設定プロパティを提供する `Settings` クラス:
    - J-Quants, kabuステーション, Slack, DB パスなどをプロパティ経由で取得。
    - 必須環境変数未設定時は `ValueError` を送出する `_require` を導入。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）を実装。
    - `is_live` / `is_paper` / `is_dev` の便利プロパティ。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP (`news_nlp`)
    - raw_news / news_symbols を元に銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）へバッチで送信してセンチメントスコアを算出。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに使用）。
    - バッチ & トリム: 銘柄あたり最大記事数／文字数で制限（過負荷抑制）。
    - バックオフ付きリトライ（429, ネットワーク断, タイムアウト, 5xx）。
    - レスポンス検証: JSON パース、results リスト、code/score の妥当性チェック、未知コード除外、数値クリップ（±1.0）。
    - 書き込みは部分置換方式（DELETE → INSERT）で idempotent に実行。DuckDB の executemany の制約に配慮（空リストを無視）。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（`_call_openai_api` を patch 可能）。
  - 市場レジーム判定 (`regime_detector`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次でレジームを判定（bull / neutral / bear）。
    - マクロニュースは `news_nlp.calc_news_window` を用いてウィンドウを算出し、マクロキーワードで抽出。
    - OpenAI（gpt-4o-mini）を JSON モードで呼び出し、マクロセンチメントを取得。
    - API フェイル時のフェイルセーフ: マクロセンチメントはデフォルト 0.0（中立）で継続。
    - 冪等な DB 書き込み（BEGIN / DELETE WHERE date=? / INSERT / COMMIT）とエラー時の ROLLBACK 保護。
    - リトライや 5xx ハンドリングを含む堅牢な API 呼び出し実装。

- データプラットフォーム関連 (`kabusys.data`)
  - ETL パイプライン (`pipeline`)
    - 差分取得、保存（jquants_client 経由）、品質チェックの流れを実装する基盤関数群。
    - ETL 実行結果を表す `ETLResult` dataclass を提供（取得/保存件数・品質問題・エラー一覧など）。
    - 品質チェックは致命的なエラーでも一括検出して呼び出し元が判断できる設計（Fail-Fast ではない）。
    - 最小データ日付 `_MIN_DATA_DATE`、バックフィル日数等の設定。
  - カレンダー管理 (`calendar_management`)
    - JPX カレンダー（market_calendar）の夜間バッチ更新ジョブ `calendar_update_job` を実装（J-Quants から差分取得して保存）。
    - バックフィル、先読み、健全性チェック（未来日が大きすぎる場合はスキップ）を実装。
    - 営業日判定ユーティリティ群: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day`。
    - カレンダー未取得時は曜日ベースでフォールバック（週末は非営業日）。DB 値は優先して使用。
    - 最大探索日数制限（無限ループ防止）。

- リサーチモジュール (`kabusys.research`)
  - ファクター計算 (`factor_research`)
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損時は None）、ROE（財務データから取得）。
    - DuckDB ベースの SQL 実装。結果は (date, code) をキーとする辞書リストで返す。
  - 特徴量探索 (`feature_exploration`)
    - 将来リターン計算（horizons: デフォルト [1,5,21]、最大 252 日のバリデーション）。
    - IC（Information Coefficient）計算: Spearman（ランク相関）実装（同順位は平均ランク）。
    - 統計サマリー（count/mean/std/min/max/median）。
    - 外部依存を持たない純粋 Python 実装（pandas 等不使用）。
  - zscore 正規化ユーティリティを `kabusys.data.stats` からインポートして再公開。

### 変更 (Changed)
- トランザクションとエラー処理の強化
  - AI のスコアリング・レジーム判定・ETL・カレンダー保存など DB 書き込み処理で明示的に BEGIN/COMMIT/ROLLBACK を使い、例外発生時にロールバックを試みる設計に変更（安全性向上）。
  - DuckDB の仕様（executemany に空リスト不可）に対する回避ロジックを採用（空パラメータのときは実行をスキップ）。

- API 呼び出しの堅牢化
  - OpenAI 呼び出し周りにリトライ / バックオフ戦略を導入し、429・ネットワーク断・タイムアウト・5xx に対して再試行を行う。
  - API レスポンスのパース失敗や非致命的エラーはログ出力のうえフェイルセーフなデフォルト値（例: 0.0）にフォールバック。

### 修正 (Fixed)
- .env パーシングの改善
  - コメント・クォート内のエスケープ・export プレフィックスなど、実運用でよくある .env フォーマットに対応。
  - キーが空や不正な行は無視する安全策を実装。

### 注意点 / 既知の設計上の制約 (Notes)
- 全ての日付処理はルックアヘッドバイアス防止のため、内部で `datetime.today()` / `date.today()` を参照しない設計の関数が多い（呼び出し側が `target_date` を渡す必要あり）。
- OpenAI API の呼び出しは gpt-4o-mini を想定し JSON mode を使用するプロンプトとレスポンス整形を前提としている。API キーは引数で注入可能（テスト時に差し替え可能）。
- DB 書き込みは部分置換（該当コードのみ DELETE → INSERT）を採用しており、部分失敗時に他コードの既存データを保護する設計。
- DuckDB を使用する前提のため、環境やバージョン差での微妙な SQL バインド挙動（特に配列バインド等）に注意。実装内で互換性対策（個別 DELETE via executemany 等）を施している。
- .env の自動ロードはプロジェクトルート検出に成功した場合のみ行われ、ライブラリがパッケージ化された後も意図した挙動となるよう配慮している。自動ロードが不要な環境（CI/テスト等）では `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。

### セキュリティ (Security)
- 現時点で重大なセキュリティ修正はありません。環境変数・APIキーの取得は `Settings` 経由で行われ、必須キー未設定時は明示的にエラーを出すため、意図しない公開や空のキーでの動作を防止します。

---

今後のリリース候補:
- モデル変更のパラメータ化（モデル名を設定から上書き可能にする）
- J-Quants / kabu API クライアントの詳細実装とさらに細かい品質チェックルールの追加
- 実運用向け監視・アラート機能（Slack 通知など）の統合

もし CHANGELOG の記載粒度（個別ファイルごとのコミットログに近い詳細 vs 機能単位の要約）や日付表記の調整が必要であればお知らせください。