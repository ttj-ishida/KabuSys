# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
以下の内容は与えられたソースコードから推測して作成したリリースノートです（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース: kabusys - 日本株自動売買システムの基礎機能群を追加
  - パッケージメタ: src/kabusys/__init__.py にバージョン `0.1.0` と主要サブパッケージのエクスポートを追加（data, strategy, execution, monitoring）。
- 環境設定/読み込み機能（src/kabusys/config.py）
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出：.git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - .env パース処理の実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応、インラインコメントの扱い等）。
  - 環境変数保護（既存 OS 環境変数を protected として上書き制御）。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）。
  - 必須環境変数未設定時の ValueError を整備（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）。

- AI (自然言語処理) モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols からターゲットウィンドウのニュースを集約して銘柄別に OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - ニュース収集ウィンドウ計算 calc_news_window を実装（JST基準の前日15:00～当日08:30 を UTC に変換）。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数制限（最大10記事）、文字数トリム（最大3000文字）。
    - OpenAI 呼び出しでのリトライ (429, ネットワーク断, タイムアウト, 5xx) を指数バックオフで実装。
    - JSON Mode を前提に応答をパースし、レスポンス検証（results リスト、code, score の検査、未知コードの無視、数値検証）。
    - スコアは ±1.0 にクリップし、取得した銘柄のみを ai_scores に置換（DELETE → INSERT）して部分失敗時の保護を実現。
    - フェイルセーフ: API 失敗やバリデーション失敗時は例外を投げず当該チャンク/銘柄をスキップ。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算し、calc_news_window と記事抽出、OpenAI によるマクロセンチメント評価を実施。
    - OpenAI 呼び出しのリトライ/バックオフ処理、API 失敗時は macro_sentiment=0.0 として継続。
    - 合成スコアをクリップし閾値でラベル付け、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時の ROLLBACK 対応。

- Data モジュール（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB データが不完全な場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API からの差分取得と冪等保存（バックフィル、健全性チェック、API 呼び出し例外処理）。
    - 最大探索日数やバックフィル、lookahead 等のパラメータ化。
  - ETL / パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（ETL の実行結果、品質問題やエラー集約、has_errors / has_quality_errors / to_dict メソッド）。
    - 差分更新のためのユーティリティ（_get_max_date 等）およびテーブル存在チェック。
    - ETL 設計方針: 差分取得、保存（idempotent）、品質チェックの収集と継続実行。
    - etl.py で ETLResult を再エクスポート。

- Research モジュール（src/kabusys/research）
  - ファクター計算・探索機能の提供（src/kabusys/research/*）
    - calc_momentum: 1M/3M/6M リターンと ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が無効な場合は None）。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD ベース）。
    - calc_ic: スピアマン（ランク）による Information Coefficient を計算（rankユーティリティを内部で使用）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクとするランク変換実装（丸めで ties 対策）。
  - research/__init__.py で主要関数を再エクスポート。

- 共通実装/設計方針
  - DuckDB を主要なローカルデータストアとして利用（全モジュールが DuckDB 接続を引数に受ける設計）。
  - ルックアヘッドバイアス回避のため、datetime.today() / date.today() を直接参照しない設計方針を明示的に採用（target_date ベースの処理）。
  - OpenAI クライアント呼び出し箇所で差し替え可能に実装（テストで unittest.mock.patch によりモック可能）。
  - ロギングと警告出力を多用し、安全性と運用性を向上（API 失敗時のフェイルセーフ、ROLLBACK の失敗ログ等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の必須トークンは Settings 経由で取得し、未設定時は明示的に例外を発生させる設計（キー漏洩防止のため、.env 自動読み込みは環境変数優先・既存 OS 変数を保護）。

---

注記: 上記は提供されたソースコードから機能・設計・挙動を推測してまとめた CHANGELOG です。実際のコミットメッセージや開発履歴に基づく正確な差分ログが必要な場合は、git の履歴やリポジトリのタグ情報を参照してください。