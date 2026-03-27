# Changelog

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys。ライブラリのエントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数を自動読込（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env と .env.local の読み込み順を実装（.env.local が上書き）。既存 OS 環境変数は保護（protected）して上書きを防止。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読込を無効化可能。
  - 高度な .env パーサ実装（export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
  - Settings クラスを提供（J-Quants / kabu ステーション / Slack / DB パス / システム設定などのプロパティを露出）。
  - KABUSYS_ENV / LOG_LEVEL の値検証および is_live / is_paper / is_dev の補助プロパティ。

- データ基盤（src/kabusys/data/*）
  - ETL 用の公開インターフェース ETLResult（dataclass）を追加（pipeline モジュールの結果表現）。
  - ETL パイプライン（data/pipeline.py）: 差分取得・保存・品質チェックの骨格を実装。DuckDB を前提とした最大日付取得やテーブル存在確認等のユーティリティを提供。
  - マーケットカレンダー管理（data/calendar_management.py）:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時は曜日ベースでフォールバックする堅牢な実装。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants から差分取得、バックフィル、健全性チェック、冪等保存の処理を実装。
    - 最大探索日数・バックフィル日数・先読み日数等の定数を提供し、安全に運用できる設計。

- リサーチ / ファクター（src/kabusys/research/*）
  - ファクター計算（research/factor_research.py）:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR・相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を結合して PER / ROE を算出。
    - DuckDB 上で SQL を利用して高効率に計算する設計。
  - 特徴量探索（research/feature_exploration.py）:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位の平均ランクを返すランク変換ユーティリティ。
  - research パッケージで主要関数を再エクスポート。

- AI（src/kabusys/ai/*）
  - ニュース NLP（ai/news_nlp.py）:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）でセンチメント評価を行い、ai_scores テーブルへ書き込み。
    - JST のニュースウィンドウ計算（前日15:00 JST〜当日08:30 JST）を calc_news_window で提供し、UTC 比較用に変換。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数・最大文字数トリム、JSON mode を用いた厳密なレスポンス処理。
    - API 呼び出しに対するリトライ（429・ネットワーク断・タイムアウト・5xx を対象）と指数バックオフ、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - DuckDB の executemany の空リスト制約に対する安全対策（空の場合は実行しない）。
  - 市場レジーム判定（ai/regime_detector.py）:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出は keywords ベース、LLM 呼び出しの失敗は macro_sentiment = 0.0 とするフェイルセーフ設計。
    - OpenAI クライアントの呼び出しは内部でラップしリトライ処理を持つ。
    - ルックアヘッドバイアスを避ける設計（datetime.today() を参照しない、DB クエリで date < target_date を厳守）。
  - ai パッケージで score_news と score_regime を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なしだが、堅牢性・フォールバックの処理を多数実装）
  - .env パーサの不適切な引用符やエスケープ処理、インラインコメント処理に対応。
  - OpenAI 呼び出しにおける様々なエラーケース（429/接続エラー/タイムアウト/5xx）に対するリトライ戦略を実装し、API の一時障害でも処理継続するように設計。
  - DuckDB 特有の制約（executemany の空リスト不可）への対応を実装。
  - market_calendar 未取得時の一貫した曜日フォールバックなど、データ欠如時の安全な挙動を確保。

### Security
- OpenAI API キーは引数で注入可能（テスト性向上）かつ環境変数 OPENAI_API_KEY を使用。未設定時は明示的にエラーを返すことで誤った運用を防止。

### Deprecated
- なし

### Removed
- なし

### Notes / Known limitations
- strategy / execution / monitoring モジュールの公開名が __all__ に含まれているが、本リリースの差分では一部機能が未実装の可能性があります。今後のリリースで追加されます。
- OpenAI の呼び出しは gpt-4o-mini + JSON mode を前提としているため、モデル・API 仕様の変更時には対応が必要です。
- 初回リリースでは各保存先（DuckDB テーブル等）のスキーマが期待通りに存在することを前提としています。導入時は DataPlatform のスキーマ準備を行ってください。

---

今後のリリースでは、戦略（strategy）/ 発注（execution）/ 監視（monitoring）関連の実装、品質チェック強化、より詳細なモニタリング機能や CI 向けのテストヘルパーの追加を予定しています。