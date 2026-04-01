# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
この CHANGELOG はリポジトリ内のコード（モジュール・関数・設計ノート）から推測して作成したもので、実際のコミット履歴とは差異がある場合があります。

各リリースの日付は推測に基づき設定しています。実際のリリース日が判明している場合は適宜更新してください。

## [Unreleased]

- 予定 / 今後の作業（コードからの推測）
  - 単体テスト・統合テストの追加（OpenAIやJ-Quants呼び出しのモック／フェイクの拡充）
  - ドキュメント（ユーザガイド・運用手順・デプロイ方法）の整備
  - Strategy / Execution / Monitoring モジュールの実装・公開（パッケージ __all__ に含まれるが実装が未検出）
  - CI/CD、リリースパイプラインの整備
  - セキュリティ監査（秘匿情報・トークン取り扱いの追加検討）

---

## [0.1.0] - 2026-04-01

初期公開（推測）。以下の主要機能・設計方針を実装。

### 追加 (Added)

- パッケージ初期設定
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）
  - public API のエクスポート候補: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび環境変数からの設定読み込み機能を実装
    - 自動ロードの優先順位: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応
    - プロジェクトルートの自動検出ロジック（.git または pyproject.toml を探索）
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープをサポート）
  - 環境変数保護（既存 OS 環境変数を protected として上書き回避）
  - settings オブジェクト（Settings クラス）を公開
    - J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / ログレベル / 環境判定プロパティを提供
    - env / log_level のバリデーション（許容値チェック）
    - Path 型を返すプロパティ（duckdb_path, sqlite_path, pid_file_path）

- AI (自然言語処理) モジュール (src/kabusys/ai)
  - ニュースセンチメント (news_nlp.py)
    - 日次ニュースウィンドウ計算（JST 基準のウィンドウを UTC naive datetime に変換）
    - raw_news と news_symbols から銘柄毎に記事集約（記事数・文字数トリム）
    - OpenAI（gpt-4o-mini、JSON Mode）を用いたバッチスコアリング（最大バッチサイズ 20）
    - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実施
    - レスポンス検証ロジック（JSON 抽出、results 配列・code/score 検証、数値クリップ ±1.0）
    - ai_scores テーブルへの冪等的な置換（該当コードのみ DELETE → INSERT）
    - テスト容易性のため OpenAI 呼び出し関数を patch 可能に設計
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成し市場レジーム（bull/neutral/bear）を判定
    - prices_daily / raw_news / market_regime を参照し日次で判定・DB へ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - マクロニュース抽出（マクロキーワード一覧を定義）と LLM 呼び出し（gpt-4o-mini、JSON Mode）
    - API エラーやレスポンスパース失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）
    - 再試行とログを備えた堅牢な実装
    - OpenAI API キー注入（引数 or 環境変数 OPENAI_API_KEY）、未指定時は ValueError

- データ基盤モジュール (src/kabusys/data)
  - ETL パイプラインインターフェース (pipeline.py / etl.py)
    - ETLResult dataclass を導入（取得件数・保存件数・品質問題・エラー等を保持）
    - 差分更新・バックフィル戦略・品質チェック設計（quality モジュールとの連携を想定）
    - DuckDB 接続を前提としたテーブル存在チェックや最大日付取得ユーティリティ
    - etl.py で ETLResult を再エクスポート
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar を用いた営業日判定ロジックを実装
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 未登録日は曜日（土日）ベースのフォールバック
    - next/prev_trading_day に最大探索日数制限を導入して無限ループを防止
    - calendar_update_job: J-Quants API から差分取得 → 保存（バックフィル日数の再取得、サニティチェック、例外ハンドリング）
    - J-Quants クライアント呼び出しは jquants_client モジュールを利用する想定
  - jquants_client / quality など外部モジュールとの連携を前提に設計（実装は分離）

- リサーチ（研究）モジュール (src/kabusys/research)
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー系ファクター計算を実装
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（MA200 は 200 日）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ATR は 20 日）
      - calc_value: per / roe（raw_financials から最新レコードを取得）
    - DuckDB のウィンドウ関数を活用した SQL ベースの計算
    - データ不足時は None を返す挙動
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（任意ホライズン、LEAD を用いた実装）
    - calc_ic: スピアマンのランク相関（IC）計算（ties は平均ランクで処理）
    - rank: 同順位の平均ランク化を含むランク化ユーティリティ
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数
  - 研究向けユーティリティは外部依存を避け、DuckDB と標準ライブラリで完結する設計

- テスト性・堅牢性に関する設計上の配慮
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を直接参照しない設計（すべて target_date ベースで計算）
  - OpenAI 呼び出しやファイル読み込み失敗時のフェイルセーフ（デフォルト値やロギングで継続）
  - API 呼び出しに対するリトライ（指数バックオフ）、5xx とそれ以外の扱いの分離
  - DuckDB 互換性配慮（executemany の空リスト回避等）
  - DB 書き込みは冪等性を意識（DELETE→INSERT や ON CONFLICT を想定）

### 変更 (Changed)

- 初回リリースのため該当なし（初期追加が中心）

### 修正 (Fixed)

- 初回リリースのため該当なし（実装時に防御的なエラーハンドリングを多数導入）

### 既知の制約・注意点（ドキュメント的補足）

- OpenAI に依存する機能は API キー（OPENAI_API_KEY）必須。キー未設定時は ValueError を発生させる設計。
- DuckDB を前提とした設計であり、該当テーブル（prices_daily 等）が存在しない場合、多くの関数は None 返却や空リスト返却を行う。
- news_nlp と regime_detector はそれぞれ独立した OpenAI 呼び出しラッパーを持ち、意図的にモジュール間で内部関数を共有しない設計（テストのためモック可能）。
- .env パーサは一般的なシェル形式の .env ファイルの多くのケースに対応するが、極端なケースでは期待通りに動作しない可能性あり。
- strategy / execution / monitoring の公開は __all__ に含まれているが、コード一覧内で完全な実装が確認できないため、実装は別コミットまたは別パッケージに存在する可能性あり。

---

参照: Keep a Changelog (https://keepachangelog.com/en/1.0.0/)