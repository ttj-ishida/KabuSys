# Changelog

すべての重要な変更点はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣例に準拠します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を追加。
  - パッケージ公開:
    - src/kabusys/__init__.py によるパッケージ初期化と __version__ = "0.1.0"。
    - 公開サブパッケージ: data, research, ai, などを __all__ で定義。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に探すため、CWD に依存しない動作。
  - .env パーサ実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（`#` の直前が空白/タブの場合のみコメント扱い）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN（必須）、KABU_API_PASSWORD（必須）など必須/任意の環境変数プロパティ。
    - デフォルト値（kabu_api_base_url、データベースパス、PID/kill flag パス 等）の設定。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（有効値を限定）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を使用して銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書込む機能を実装。
  - 主な仕様:
    - ニュース対象ウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC に変換して DB と照合）。
    - 1 銘柄あたり最大 _MAX_ARTICLES_PER_STOCK 件・文字数トリム（_MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄ずつのバッチ送信（_BATCH_SIZE）。
    - レート制限・ネットワーク断・タイムアウト・5xx の際は指数バックオフでリトライ。非再試行エラーはスキップ。
    - OpenAI の JSON Mode 結果をバリデーション（results リスト・コード整合性・スコア数値性など）。不正なレスポンスはスキップ。
    - スコアは ±1.0 にクリップ。
    - 書込みは冪等性を考慮（取得済みコードのみ DELETE → INSERT）し、DuckDB 0.10 の executemany 空リスト制約を扱う。
    - テスト性のため api_key 引数でキー注入可能、内部の API 呼び出しは差し替え可能（_call_openai_api を patch）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジームを判定（bull/neutral/bear）。
  - 処理の特徴:
    - ma200_ratio は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
    - マクロニュースはマクロキーワードでフィルタし、OpenAI（gpt-4o-mini）に JSON 出力を要求して macro_sentiment を取得。
    - API エラー時は macro_sentiment=0.0 にフォールバック（例外を上げず継続）。
    - レジームスコア合成後、market_regime テーブルへトランザクション内で冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。書込み失敗時は ROLLBACK。
    - テストのため api_key 注入可、内部 OpenAI 呼び出しは独立実装でモジュール間の結合を低減。

- データプラットフォーム（src/kabusys/data/*）
  - マーケットカレンダー管理（calendar_management.py）
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day の API を提供。
    - market_calendar が存在しない場合は土日ベースのフォールバックを採用して一貫性を確保。
    - next/prev は最大探索範囲制限（_MAX_SEARCH_DAYS）で無限ループを防止。
    - calendar_update_job を実装: J-Quants API から差分取得し market_calendar を保存（バックフィル・健全性チェック含む）。
    - jquants_client の fetch/save を利用（外部クライアント経由）。

  - ETL パイプライン基盤（pipeline.py / etl.py）
    - ETLResult データクラスで ETL 実行結果を集約（フェッチ数、保存数、品質問題、エラー概要など）。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した骨組み。
    - 品質チェックは重大度情報を持ちつつ、ETL 自体は可能な限り継続（Fail-Fast にはしない設計）。
    - jquants_client を用いた idempotent な保存（ON CONFLICT DO UPDATE）を想定。

- リサーチ機能（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。ウィンドウ不足は None を返す。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得して PER/ROE を計算。EPS が 0/欠損の場合は None。
    - いずれも DuckDB のウィンドウ関数を利用し、prices_daily / raw_financials のみ参照。外部 API にアクセスしない安全設計。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来終値からリターンを計算。horizons の妥当性チェック（正の整数かつ <=252）。
    - calc_ic: Spearman のランク相関（ρ）を算出、データが不足 ( <3 ) の場合は None。
    - rank: 同順位は平均ランク扱い。丸め（round(v,12)）により浮動小数点の ties 検出漏れを防止。
    - factor_summary: count/mean/std/min/max/median を算出（None 値は除外）。標準ライブラリだけで実装。

- パッケージ化・インポート整理
  - ai/__init__.py, research/__init__.py, data/etl.py などで主要 API を再エクスポートし、外部利用を簡潔化。

### Security
- LLM 機能（news_nlp / regime_detector）は OpenAI API キーを必要とし、api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合は ValueError を発生させるよう明示。

### Notes / Design highlights
- ルックアヘッドバイアス対策:
  - ニュース・レジーム・ファクター計算は内部で datetime.today()/date.today() を参照しない。関数呼び出し側が target_date を明示的に渡す設計。
  - DB クエリは target_date 未満 / 指定範囲の排他条件を用いて将来データ参照を防止。
- テスト性:
  - OpenAI 呼び出しを抽象化（内部の _call_openai_api を patch 可能）し単体テストを容易化。
  - api_key の注入や自動 env ロード無効化フラグで外部依存を切り離せる。
- DuckDB に依存する実装上の留意点（例: executemany に空リスト不可）に対応するためのガード処理を導入。
- ロギング: 重要なフォールバックや例外時は警告/情報ログを出力して診断を容易に。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

---

（参考）バージョン参照リンク
- [Unreleased]
- [0.1.0] - 2026-04-03

注: ここに記載した内容は提供されたコードベースからの推測に基づく CHANGELOG です。実際のリポジトリ履歴やリリースノートがある場合はそれに合わせて調整してください。