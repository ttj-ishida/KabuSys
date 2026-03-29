# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠して記載します。  
日付はコードベースから推測できる現在日時（2026-03-29）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース（コードベースから推測） — 日本株自動売買 / 研究 / データ基盤用ユーティリティ群を含む最小実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期エントリーポイントとバージョン管理を追加（__version__ = "0.1.0"）。
  - package-level の公開モジュール指定（__all__ に data, strategy, execution, monitoring を宣言）。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定値を自動読み込みする仕組みを実装：
    - プロジェクトルートの検出（.git または pyproject.toml を起点）により CWD に依存しない自動ロード。
    - 読み込み順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数に対応。
  - 高機能な .env パーサを実装：
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート中のバックスラッシュエスケープ処理をサポート。
    - クォート無しの場合のインラインコメント処理（# の前が空白/タブのときのみコメントと認識）。
  - 上書き動作と保護鍵（protected）をサポートし、OS 環境変数を保護する設計。
  - Settings クラスを公開し、主要設定プロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH, SQLITE_PATH（デフォルト値あり）
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) のバリデーション（有効値セットを定義）
    - ユーティリティプロパティ: is_live / is_paper / is_dev

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチで問い合わせてセンチメントスコアを算出。
    - タイムウィンドウ計算（JST基準 → UTC に変換）: 前日 15:00 JST ～ 当日 08:30 JST。
    - バッチサイズ制限 (_BATCH_SIZE=20)、1銘柄あたりの最大記事数/文字数制限（トークン肥大化対策）。
    - JSON Mode を利用し厳密な JSON 出力を期待。レスポンスに対する堅牢なバリデーション実装。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ、失敗時はスキップしてフェイルセーフにフォールバック。
    - 結果は ai_scores テーブルへ冪等的に置換（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に設計 (unittest.mock.patch を想定)。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei225 連動）の 200日移動平均乖離（重み 70%）と、news_nlp によるマクロニュースセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは gpt-4o-mini を利用、JSON レスポンスのパースと冗長なエラーハンドリング（リトライ・ステータス判別）。
    - API 失敗時は macro_sentiment=0.0 を採用するフェイルセーフ挙動。
    - データベースへの書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。例外時に ROLLBACK を試行し、失敗ログを出力。

- データモジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダーの夜間バッチ更新ジョブ (calendar_update_job) を実装（J-Quants クライアント経由で差分取得 → 保存）。
    - market_calendar テーブルが未取得時のフォールバック（曜日ベース: 土日非営業）を実装。
    - 営業日判定 / 次の営業日 / 前の営業日 / 期間内の営業日列挙 / SQ 日判定のユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - 最大探索幅・バックフィル・健全性チェックを備え、DB データがまばらでも一貫した挙動を維持。
  - ETL パイプライン (pipeline)
    - データ差分取得・保存・品質チェックフローを実装するための ETLResult データクラスを追加（取得数・保存数・品質問題・エラー集約）。
    - テーブル最大日付取得や存在チェック等のユーティリティを実装。
    - デフォルトのバックフィルやカレンダー先読みの定義（_DEFAULT_BACKFILL_DAYS, _CALENDAR_LOOKAHEAD_DAYS など）。
    - jquants_client と quality モジュール経由でのデータ取得・品質チェック設計を明示。
  - ETL の公開インターフェースを etl.py 経由で提供（ETLResult を再エクスポート）。

- 研究モジュール (kabusys.research)
  - ファクター計算 (research.factor_research)
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離の計算（データ不足時の None 処理）。
    - Volatility / Liquidity: 20日 ATR（true range の扱いに注意）、相対 ATR、20日平均売買代金、出来高比率等を計算。
    - Value: 最新の raw_financials を参照して PER / ROE を算出（EPS が 0 または欠損時は None）。
    - すべて DuckDB 上の SQL とウィンドウ関数で実装、外部 API 呼び出しなしで再現性を確保。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を一回のクエリで取得。
    - IC（Information Coefficient）計算: スピアマンランク相関を実装（結合・None 除外・最小サンプルチェック）。
    - ランク変換ユーティリティ（同順位は平均ランク、丸めによる ties 回避）。
    - ファクター統計サマリー（count/mean/std/min/max/median）を標準ライブラリのみで実装。
  - 研究用 API をパッケージ外部にエクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- 初版のため過去リリースからの変更は無し。

### 修正 (Fixed)
- 初版のため既知のバグ修正履歴は無し。

### 既知の設計上の注意点 / フェイルセーフ
- AI 呼び出し失敗時は例外を上位に投げず、スコア未取得部分はスキップし既存データを保護する設計（安全優先）。
- 日付計算は datetime.today() / date.today() を直接参照しない設計方針が各所に反映されている（ルックアヘッドバイアス対策）。
- DuckDB のバージョン差異に配慮した実装（executemany の空リスト回避や list バインド回避など）。
- OpenAI との統合はテスト容易性を考慮して呼び出し箇所の差し替えを想定。

---

今後のリリースで期待される改善点（想定）
- strategy / execution / monitoring の実装（現在はモジュール名のみ公開）。
- jquants_client / quality モジュールの具体的実装の共有・安定化。
- 追加のテストベクター（外部 API のモック、DuckDB の複数バージョン対応テスト）。
- パフォーマンス改善（大規模データでのクエリ最適化、並列処理など）。

---
（注）本 CHANGELOG は提供されたコードの内容から推測して作成したものであり、実際のコミット履歴やリリースノートではありません。必要であれば日付・詳細を実際の履歴に合わせて調整してください。