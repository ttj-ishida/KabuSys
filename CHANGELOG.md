# CHANGELOG

すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

- 表記ルール: 変更は大きく Added / Changed / Fixed / Security に分類しています。  
- 日付はリリース日です。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期バージョンを追加（kabusys v0.1.0）。
  - パッケージ公開インターフェースを __all__ で定義（data, strategy, execution, monitoring）。

- 環境・設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートを .git / pyproject.toml から探索して .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env の堅牢なパーサを実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォートのエスケープ処理対応
    - インラインコメントの扱い（クォートあり/なしでの振る舞い）に対応
  - 環境変数の上書き制御: override と protected キー群（OS 環境変数の保護）をサポート。
  - Settings クラスを提供し、プロパティ経由で各種設定（J-Quants, kabuステーション, Slack, DB パス, 環境種別、ログレベル等）を取得・バリデーションする。
  - KABUSYS_ENV と LOG_LEVEL の有効値検証を実装（不正値は ValueError）。

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータが無い場合の曜日ベースフォールバックを実装。
    - 最大探索日数・バックフィル・健全性チェック等を組み込み、無限ループや過剰フェッチを防止。
  - ETL パイプラインインタフェース（pipeline.ETLResult を etl モジュールで再エクスポート）。
  - ETL 実装（pipeline）:
    - ETLResult データクラス（取得件数、保存件数、品質チェック結果、エラー集約など）。
    - 差分取得、バックフィル、品質チェックの設計を反映するユーティリティ関数群。
    - DuckDB を前提としたテーブル存在チェック・最大日付取得などを実装。
    - jquants_client / quality モジュールと連携するためのフックを用意。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（research.factor_research）:
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日ATR、相対ATR、出来高指標）、Value（PER, ROE）等の計算関数を追加。
    - DuckDB 上で SQL とウィンドウ関数を活用して計算を実行。
  - 特徴量探索（research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応・入力検証）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）。
    - ランク関数（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）。
  - zscore_normalize は data.stats から再エクスポート。

- AI モジュール（kabusys.ai）
  - ニュース NLP（news_nlp）:
    - raw_news + news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）を用いたバッチセンチメント解析を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の厳密な計算（UTC naive datetime を返す calc_news_window）。
    - 銘柄あたり記事数・文字数上限（トークン肥大化対策）。
    - バッチ送信（最大 20 銘柄／チャンク）、JSON Mode によるレスポンス受信、バリデーション、スコアの ±1.0 クリップ。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実行。
    - DuckDB での部分置換（該当コードのみ DELETE → INSERT）により部分失敗の影響を限定。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）を行う score_regime を実装。
    - ma200_ratio の計算（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - マクロキーワードで raw_news をフィルタリングしてタイトルを LLM に渡すロジック、LLM の再試行・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
    - レジーム判定結果を market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。

### Fixed
- LLM レスポンス処理の堅牢化
  - news_nlp と regime_detector の JSON パースにおいて、JSON mode でも前後に余計なテキストが混入するケースを想定し、最外の波括弧 {} を抽出して復元するロジックを実装。
  - レスポンスの想定外構造（キー欠如・型不整合）に対して例外を上位に伝播させず、警告ログを出してスキップするフェイルセーフを導入。

- データベース書き込み時の回復性
  - score_regime / score_news にてトランザクション（BEGIN / COMMIT / ROLLBACK）の使用と、ROLLBACK が失敗した場合の警告ログ出力を実装して DB 一貫性の保護を強化。
  - DuckDB の executemany が空リストを受け付けない制約に対応するため、空でないことを確認してから executemany を呼ぶ安全措置を追加。

- 時刻・期間の扱い
  - ニュースウィンドウ・レジーム判定等の関数群は datetime.today() / date.today() を直接参照せず、明示的な target_date を受け取る設計に統一（ルックアヘッドバイアスを防止）。

### Security
- 環境変数ロードの安全化
  - .env 自動ロード時、既存の OS 環境変数を protected として保護する機構を実装（.env による意図しない上書きを防止）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで無効化可能（テスト環境向け）。
- OpenAI API キーの必須チェック
  - news_nlp / regime_detector で api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合は ValueError を発生させ、誤った無保証実行を防止。

### Notes / Design decisions
- 外部依存の最小化:
  - 研究・集計コードは pandas 等の重い外部ライブラリに依存せず、標準ライブラリと DuckDB の SQL 機能で実装。
- DuckDB 前提設計:
  - 多くの集計・ウィンドウ処理は DuckDB 用の SQL を想定して実装（情報スキーマや window 関数の利用）。
- フェイルセーフ優先:
  - ネットワーク障害や LLM の不正レスポンス発生時でも全体処理が停止しないように設計（可能な範囲でスキップ・デフォルト値を利用）。
- テストしやすさ:
  - OpenAI 呼び出し箇所は内部のラッパー関数を用意しており、ユニットテスト時にモック差し替えが可能。

---

今後の予定（例）:
- strategy / execution / monitoring モジュールの具体実装（本リリースではデータ・研究・AI 周りの基盤を中心に実装）。
- J-Quants / kabu ステーション用クライアントの補完、監視・通知機能の強化。