# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-26
初期リリース — 日本株自動売買システムのコアライブラリを公開。

### Added
- パッケージの基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py）

- 環境・設定管理
  - .env ファイルおよび環境変数から設定を自動的に読み込む仕組みを実装（src/kabusys/config.py）。
    - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に探索し、自動ロードを行う（CWD非依存）。
    - `.env` / `.env.local` の読み込み順序をサポート。OS 環境変数を保護する protected オプションを実装。
    - .env のパースロジック強化: export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなどを考慮。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - Settings クラスを提供し、各種必須設定（J-Quants, kabuAPI, Slack, DB パス 等）をプロパティ経由で取得。値検証（環境種別、ログレベル等）を実装。

- AI (自然言語処理 / レジーム推定)
  - ニュース NLP スコアリングモジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを組み、OpenAI (gpt-4o-mini) にバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチサイズ、記事数・文字数トリム、JSON mode を用いた出力期待、レスポンス検証、スコアの ±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、API呼び出し失敗時のフェイルセーフ（スキップ）を実装。
    - DuckDB の executemany に関する互換性問題へ対応（空リスト送信防止）。
  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei連動）の 200日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出、OpenAI 呼び出し、再試行戦略、フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）
    - ボラティリティ/流動性: 20日 ATR、相対ATR、20日平均売買代金、出来高比率
    - バリュー: PER（EPS 有効時）、ROE（raw_financials から取得）
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials のみ参照）。外部 API や取引実行へのアクセスは無し。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Information Coefficient）計算（スピアマンランク相関）
    - ランク変換ユーティリティ（同順位は平均ランク）
    - 統計サマリー（count/mean/std/min/max/median）を実装
    - pandas 等外部依存なしで実装

- データ（Data）モジュール
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar が未取得状況では曜日ベース（週末除外）でフォールバックする一貫したロジック。
    - JPX カレンダー差分取得バッチ job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・冪等保存を行う（バックフィル・健全性チェックあり）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得件数 / 保存件数 / 品質チェックの問題 / エラー一覧 を保持）。
    - 差分更新、backfill（再取得）、品質チェックの流れを想定した設計（jquants_client と quality モジュールを統合）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。

- その他
  - モジュール間の疎結合を意識した設計（AI モジュール間でプライベート呼び出し関数を共有しない等）。
  - ルックアヘッドバイアス防止: いずれの処理も datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
  - DuckDB を前提とした SQL / トランザクション処理（BEGIN/COMMIT/ROLLBACK）を各所で適切に利用。
  - 詳細なログ出力（logger）を各処理に追加。

### Changed
- 初版につき該当なし。

### Fixed
- 初版リリース時点でコード中に以下の堅牢化対策を実装済み
  - OpenAI API 呼び出しに対するリトライとバックオフ（RateLimit / 接続断 / タイムアウト / 5xx の扱いを明確化）。
  - OpenAI レスポンスの JSON パース失敗時の回復ロジック（最外側の {} を抽出する等）。
  - DuckDB の executemany に空リストを渡すと失敗する問題の回避（空チェックを追加）。
  - DB 書き込み失敗時の ROLLBACK とその失敗時の警告ログ出力。
  - .env 読み込み失敗時の警告・例外回避。

### Security
- 初版につき特記事項なし。ただし、OpenAI API キー等の秘密情報は Settings 経由で環境変数から参照する仕様。OS 環境変数を上書きしない保護機構を提供。

### Notes / Known limitations
- AI モジュールは OpenAI (gpt-4o-mini) へのネットワーク依存があり、API 利用料金やレート制限に影響を受ける。
- ETL / データ取得は jquants_client / quality モジュールに依存しており、外部 API クライアントの実装や認証が必要。
- 一部処理（例: PBR・配当利回りなどのバリュー指標）は未実装（将来拡張予定）。
- DuckDB バージョン差異に起因する SQL バインディングの互換性を考慮した実装になっているが、実運用前に環境合わせたテスト推奨。

----

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートやプロジェクトのポリシーに合わせて適宜編集してください。