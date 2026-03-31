# Changelog

すべての注目すべき変更履歴をここに記録します。本ファイルは Keep a Changelog のスタイルに準拠しています。  
フォーマット: [Unreleased] → リリース済みバージョン（日時付き）。  

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-03-31

初回リリース（ベース実装）。主な追加・実装内容は以下の通りです。

### Added
- パッケージの初期エントリポイント
  - src/kabusys/__init__.py にてバージョン番号と公開モジュール一覧を定義（__version__ = "0.1.0"）。
  - パッケージ外部に公開する主要サブパッケージの概念（data, strategy, execution, monitoring）。

- 設定／環境変数管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロードの挙動:
    - プロジェクトルートは .git または pyproject.toml を基準に探索（cwd に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサは以下に対応:
    - export KEY=val 形式
    - シングル／ダブルクォート内のエスケープ処理
    - インラインコメントの扱い（クォートなしでは直前に空白・タブがあればコメントとみなす）
  - 必須変数取得用の _require() と、環境値検証（KABUSYS_ENV, LOG_LEVEL）の実装。
  - 主要設定プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等。

- データ（Data platform）周り
  - ETL パイプライン結果データクラス ETLResult を公開（src/kabusys/data/pipeline.py / etl.py にて再エクスポート）。
    - 取得件数・保存件数・品質チェック結果・エラー情報を保持。has_errors / has_quality_errors 等の便宜メソッドを提供。
  - market カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定・SQ判定・前後営業日探索・期間内営業日取得のユーティリティを提供。
    - calendar_update_job により J-Quants API から差分取得して冪等的に保存する仕組みを実装（バックフィル、健全性チェック含む）。
    - DB データが存在しない場合は曜日ベースのフォールバック（週末は非営業日）を行う設計。
  - ETL パイプライン補助（src/kabusys/data/pipeline.py）
    - 差分更新、バックフィル、品質チェック連携（quality モジュール利用）、DuckDB を前提とした実装。
    - テーブル存在チェックや最大日付取得ユーティリティを実装。

- 研究・リサーチモジュール（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などモメンタム系ファクターを計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: 最新の raw_financials を基に PER / ROE を計算。
    - DuckDB SQL を活用した効率的かつ一貫した実装。データ不足時の None 返却等を扱う。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターン (1/5/21営業日等) を計算（複数ホライズン同時取得）。
    - calc_ic: スピアマンのランク相関による IC 計算（欠損やサンプル不足を考慮）。
    - rank, factor_summary: ランク変換・基本統計量集計ユーティリティを提供。
  - すべての研究関数は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しないことでルックアヘッドバイアスを回避。

- AI（自然言語処理）モジュール（src/kabusys/ai/*）
  - news_nlp.py:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を生成。
    - バッチング（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数・文字数トリム、レスポンスバリデーション、スコアクリップ (±1.0) を実装。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ、その他はスキップ（フェイルセーフ）。部分失敗時は既存の他銘柄スコアを保持するため書き込みはコード単位で DELETE→INSERT。
    - calc_news_window: タイムウィンドウ（JST基準）を UTC ナイーブ datetime として計算（前日15:00～当日08:30 JST 相当の UTC 範囲）。
  - regime_detector.py:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で判定結果を保存する score_regime を実装。
    - マクロニュースはタイトルベースでマクロキーワードフィルタ（定義済キーワード群）して最大 N 件を LLM に渡す。API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - _call_openai_api はテスト時に差し替え可能で、news_nlp とは別実装にしてモジュール結合を避ける。
    - DB 書き込みは冪等化（BEGIN / DELETE / INSERT / COMMIT）し、例外時は ROLLBACK を試行して上位へ伝播。
  - OpenAI 連携に関しては API キー注入（引数 or OPENAI_API_KEY 環境変数）をサポート。

- 例外処理・運用性の改善
  - 各所でログ（logger）により状態・警告・エラーを記録。
  - リトライやデグレード（代替値）を用いたフェイルセーフ設計（例: ma200_ratio 不足時は中立 1.0、LLM 失敗時は 0.0）。
  - DuckDB に対する executemany の空リスト制約への対処（空なら実行しない）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

注記:
- 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートや仕様書と差異がある場合があります。