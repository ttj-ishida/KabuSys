# Changelog

すべての変更は Keep a Changelog の仕様に準拠します。  
安定版リリースはセマンティックバージョニング（MAJOR.MINOR.PATCH）を採用します。

なお、本 CHANGELOG は提供されたコードベースからの推測に基づいて作成しています（実装上の注記・設計方針・既知挙動を含む）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-26

初回リリース — 日本株自動売買システム「KabuSys」基盤実装

### Added
- パッケージ公開情報
  - src/kabusys/__init__.py によりパッケージ名とバージョン (`0.1.0`) を定義。公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイル（`.env`, `.env.local`）および OS 環境変数からの設定読み込み自動化機能を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により CWD に依存しない読み込み。
    - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - Settings クラスを公開（必須項目取得 `_require`、既定値、検証ロジック含む）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得
      - DB パス（DUCKDB_PATH, SQLITE_PATH）と API ベース URL をデフォルト有りで取得
      - KABUSYS_ENV / LOG_LEVEL の値検証、is_live/is_paper/is_dev のユーティリティプロパティ

- AI（ニュース NLP / 市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）を用いて銘柄毎のセンチメント（-1.0〜1.0）を算出。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC へ変換）と記事トリム（記事数上限・文字数上限）を実装。
    - バッチ処理（最大 20 銘柄/回）、JSON Mode 応答検証、レスポンスバリデーション、スコアのクリップ、部分書き換え（DELETE → INSERT）による冪等保存。
    - リトライ（429/ネットワーク/タイムアウト/5xx）用の指数バックオフ実装。フェイルセーフで API 失敗時は該当チャンクをスキップ。
    - test 用の置換ポイント（_call_openai_api を patch 可能）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込み。
    - ma200_ratio の算出、マクロキーワードでの raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）とリトライ方針、フェイルセーフ時の macro_sentiment=0.0。
    - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバックの取り扱い。
    - ルックアヘッドバイアス防止の設計（date < target_date 等により未来データを参照しない）。

  - src/kabusys/ai/__init__.py で score_news を公開。

- Research（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）等のファクター計算関数を実装。
    - DuckDB 上の prices_daily / raw_financials テーブルを参照し、(date, code) をキーとする dict のリストで結果を返す。
    - データ不足時の None 処理を含む堅牢な実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（複数ホライズン対応）、Spearman ランク相関（IC）計算、ランク付けユーティリティ、ファクター統計サマリー機能を実装。
    - Pandas 等非依存で標準ライブラリのみで実装。rank 関数は同順位を平均ランクで扱う。

  - src/kabusys/research/__init__.py で主要関数を再エクスポート。

- Data（ETL / カレンダー / パイプライン）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar テーブルを参照し、未取得日は曜日ベースでフォールバック（週末除外）。最大探索日数の保護、カレンダー更新ジョブ（calendar_update_job）と J-Quants 連携のエラーハンドリングを実装。
    - バックフィル・健全性チェック・冪等保存の方針を実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基礎（差分取得、保存、品質チェック）に対応するユーティリティを実装。
    - ETLResult データクラスを導入（取得数／保存数／品質問題／エラー一覧等）と便利メソッド（to_dict, has_errors, has_quality_errors）。
    - DuckDB のテーブル存在チェック、最大日付取得等の内部ユーティリティを提供。
    - デフォルトのバックフィル日数、カレンダー先読み等の定数を定義。

  - src/kabusys/data/etl.py で ETLResult を公開。

  - jquants_client / quality 等のクライアント層と連携する設計（差分取得 → 保存 → 品質チェック）。

- DuckDB を中心としたストレージ設計
  - 多くのモジュールが DuckDB 接続（duckdb.DuckDBPyConnection）を第一引数に取る設計。
  - SQL と Python の組合せで高速な列指向処理を利用。

### Changed
- 実装方針・設計上の注記（コード内に明示）
  - すべての分析処理で datetime.today() / date.today() によるルックアヘッドバイアスを避ける設計方針が統一適用。
  - OpenAI 呼び出しに対する失敗時のフェイルセーフ（0.0 フォールバックやチャンクスキップ）を採用し、ETL/解析パイプラインの耐障害性を高めている。

### Fixed
- （初回リリースのため該当なし）

### Security
- .env 読み込み時、既存の OS 環境変数を保護するため protected セットを使用。`.env` 読み込みはデフォルトで OS 環境変数を上書きしない。
- Settings による環境変数必須チェック・値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装し、不正設定時に早期に失敗する。

### Notes / Implementation details
- OpenAI モデルは現状 gpt-4o-mini を使用するように定数化されている（news_nlp/regime_detector）。
- ニュース処理は銘柄ごとに最新記事を集約し、トークン肥大化防止のため記事数・文字数を制限。レスポンスは JSON Mode を前提に堅牢にパース・補正（外側の {} を抽出する等）する実装。
- API リトライは 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフ方式。非 5xx の APIError は基本的にリトライしない方針。
- DB 書き込みはなるべく部分的に置換（対象コードのみ DELETE → INSERT）することで、部分失敗時のデータ保護を行う。
- DuckDB のバージョン差分に配慮した実装（executemany の空リスト回避、list バインドの互換性回避等）。

---

今後の変更候補（例）
- Slack 連携の通知ユーティリティ追加
- strategy / execution / monitoring サブパッケージの具体的実装公開
- テスト用モック・ローカル開発ワークフローの改善（OpenAI モック、DuckDB テストフィクスチャ）
- パフォーマンス改善のためのバッチ/並列化・メトリクス収集の強化

（以上）