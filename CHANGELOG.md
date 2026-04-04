# CHANGELOG

すべての重要な変更をここに記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。
※この CHANGELOG は提供されたコードベースの内容から推測して記載しています。

現在の日付: 2026-04-04

## [Unreleased]

## [0.1.0] - 2026-04-04
初回公開リリース

### 追加
- パッケージ骨格
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール群のエクスポート: data, strategy, execution, monitoring（__all__ に定義）

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - プロジェクトルート検出: 現在ファイル位置から上位ディレクトリを走査して .git または pyproject.toml を検出してプロジェクトルートを特定。
  - 自動 .env ロードの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - 環境変数保護: OS の既存環境変数を protected として上書きを防止する仕組み。
  - Settings に多数のプロパティを実装（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH, PID/kill flag パス、閾値、KABUSYS_ENV 検証、LOG_LEVEL 検証など）。
  - 必須環境変数未設定時は明示的な ValueError を送出する _require 実装。

- AI（自然言語処理）関連（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を集約して銘柄ごとにニューステキストをまとめ、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントスコアを算出。
    - calc_news_window: JST 基準のニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算するユーティリティを提供。
    - score_news: スコア取得のメイン関数。最大バッチサイズ、チャンクごとのリトライ、レスポンス検証、スコアクリップ（±1.0）、DuckDB への冪等書き込み（DELETE → INSERT）を実装。
    - OpenAI 呼び出しのリトライ/バックオフ処理（429・ネットワーク断・タイムアウト・5xx を対象）。部分失敗時に他銘柄の既存スコアを保護するために書き込み対象コードを限定。
    - DuckDB の executemany の制約（空リスト不可）に合わせたガード実装。
    - レスポンス検証: JSON パース（前後ノイズ復元も試行）、results 配列、各要素の code/score 検証、未知コードの無視。

  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ書き込む score_regime を提供。
    - _calc_ma200_ratio: ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用し、データ不足時は中立 1.0 を返す。
    - マクロ記事抽出: マクロキーワードから raw_news のタイトルを抽出（最大 20 件）。
    - _score_macro: OpenAI 呼び出し（JSONレスポンス想定）とリトライロジック。API 失敗時は macro_sentiment=0.0 でフォールバックして処理継続。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。エラー時は ROLLBACK を試みて例外を伝播。

- データプラットフォーム関連（kabusys.data）
  - calendar_management
    - JPX カレンダー管理: market_calendar テーブルを利用した営業日判定、次/前営業日の検索、期間内営業日取得、SQ判定などを実装。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫した挙動を提供。
    - calendar_update_job: J-Quants API からカレンダーを差分取得し保存する夜間バッチ処理（バックフィル／健全性チェックを含む）。
    - 最大探索範囲やバックフィル、先読み日数等のパラメータ化（定数で設定）。

  - pipeline / etl
    - ETLResult データクラスを追加（ETL の取得/保存件数、品質問題、エラーの集約）。
    - pipeline モジュールの ETLResult を再エクスポートする軽量インターフェース。
    - ETL 実装方針・定数（最小日付、バックフィル、品質チェック重大度など）をコードに反映。

- 研究（research）関連（kabusys.research）
  - factor_research
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を計算（200 日 MA のデータ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算（データ不足時は None）。
    - calc_value: raw_financials から最終財務データを取得して PER / ROE を計算（EPS=0 / 欠損時は None）。
    - いずれも DuckDB SQL を用いた実装で、外部 API へアクセスしないことを保証。

  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証（正の整数かつ <=252）。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）時は None。
    - rank / factor_summary: 同順位の平均ランク算出、各カラムの count/mean/std/min/max/median を算出するユーティリティ。

### 変更（設計上の明示）
- 全体設計方針（ドキュメント記載）
  - ルックアヘッドバイアス防止のため、各種処理で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB 書き込みは冪等（上書き・DELETE→INSERT）を基本とし、部分失敗時に既存データを保護する実装方針。
  - OpenAI 呼び出しは再試行と指数バックオフを導入（再試行回数や待機時間は定数化）。
  - DuckDB のバージョン差分（executemany の空リスト不可等）への互換考慮を実装。

### 修正（フェイルセーフ / ロギング）
- AI API 呼び出しや外部 API 失敗時の安全なフォールバックを多数実装。
  - score_news / score_regime: API 失敗時は例外を上位に投げず、該当処理をスキップまたはスコアを 0 にして継続する。
  - JSON パース失敗やレスポンスの形式違いに対しては警告ログを出力して安全にスキップ。
  - DB 書き込みの例外時に ROLLBACK を試み、さらに ROLLBACK に失敗した場合は警告ログを出す処理を追加。

### 既知の制約・注意点
- OpenAI API 依存
  - score_news / score_regime の呼び出しには OPENAI_API_KEY が必要。未設定時は ValueError を送出。
  - デフォルトで使用するモデルは gpt-4o-mini（JSON Mode を利用）。API レスポンスの仕様変更やレート制限により振る舞いが変わる可能性あり。

- .env 自動ロードの挙動
  - プロジェクトルート検出に .git または pyproject.toml を利用するため、配布後や独立した配置時に検出できない場合は自動ロードをスキップする。
  - OS 環境変数の保護（上書き防止）により、.env.local があっても既存 OS 環境変数は上書きされない。

- DuckDB に関する互換性考慮
  - executemany に空リストを渡せないバージョンへの対応コードを含む（空のパラメータリストはスキップ）。
  - 日付/型の扱いで DuckDB の返却型に依存するため、_to_date 等の変換ユーティリティを用いて日付を正規化している。

- 計算上のハードコード値
  - マジックナンバー（例: 200 日移動平均、ATR 20 日、バッチサイズ 20、スコアクリップ ±1.0、MA とマクロの重み 0.7/0.3、bull/bear の閾値等）は現時点で定数として実装されている。将来的に設定化の余地あり。

### セキュリティ
- 環境変数に API キー等を期待する設計のため、運用時は .env の管理・アクセス制御に注意すること。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してテストや CI 環境で誤読を防げる。

---

この CHANGELOG はコードから読み取れる仕様・挙動を基に推測して作成しています。運用やリリースノートに利用する場合は、実際の変更履歴やリリース日、マイグレーション手順等を合わせて記載してください。必要であれば、各機能についてのより詳細な変更点や使用例、移行注意点を追加でまとめます。