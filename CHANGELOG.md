# CHANGELOG

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このファイルは主にリリース / 機能の概要・重要な実装上の注意点を示します。

## [Unreleased]

- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-04

初回公開リリース。

### 追加 (Added)

- 基本パッケージ構成
  - kabusys パッケージの公開 (version 0.1.0)
  - パブリック API の __all__ に data, strategy, execution, monitoring を設定。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルート検出は __file__ を起点に `.git` または `pyproject.toml` を探索して行う（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - .env 読み込み時、既存の OS 環境変数は保護（protected set）して上書きを防止。
  - .env パーサは以下に対応:
    - 空行 / コメント行（#）を無視
    - `export KEY=val` 形式のサポート
    - シングル/ダブルクォート内のエスケープ処理
    - インラインコメントの扱い（クォートなしでは '# ' の直前をコメント扱い）
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境（development/paper_trading/live）等のプロパティを公開。
    - 環境名やログレベルの妥当性チェックを実装（不正値は ValueError）。
    - パス型プロパティは Path に正規化して返す。

- AI（自然言語処理）機能 (kabusys.ai)
  - ニュースNLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を元に銘柄別に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode で一括センチメント評価。
    - バッチ処理 (最大 20 銘柄/API 呼び出し)、1銘柄あたりの記事数・文字数上限（記事: 10 件、文字: 3000 文字）。
    - レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - レート制限（429）、ネットワーク断、タイムアウト、5xx に対する指数バックオフでのリトライ実装。
    - 部分成功に対応するため、ai_scores テーブルへの書き込みは対象コードのみ DELETE → INSERT（冪等性・既存データ保護）。
    - テスト用に OpenAI 呼び出し関数を patch して差し替え可能（_call_openai_api をモックしやすい設計）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照し、結果を market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - LLM 呼び出しで失敗した場合は macro_sentiment=0.0 で継続するフェイルセーフ。
    - OpenAI 呼び出しは独立実装（news_nlp と意図的に分離）。
    - target_date 未満のみのデータを参照するなど、ルックアヘッドバイアスを防ぐ実装方針。

- Data / ETL / カレンダー管理 (kabusys.data)
  - calendar_management
    - market_calendar テーブルの管理、営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合は曜日ベース（土日非営業）のフォールバックを提供。
    - next/prev_trading_day は探索上限日数（_MAX_SEARCH_DAYS）を持ち、見つからない場合はエラーを返す。
    - calendar_update_job: J-Quants API からカレンダー差分取得 → 保存（バックフィル / 健全性チェックを実施）。
  - pipeline / ETL
    - ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧を含む）。
    - 差分更新、バックフィル、品質チェックとの連携方針を実装（quality モジュールと連携する想定）。
    - etl.py で ETLResult を公開（再エクスポート）。
  - DuckDB 前提の実装。DuckDB の制約（executemany に空リスト不可など）に配慮した書き込みロジックを採用。

- Research（因子・特徴量探索） (kabusys.research)
  - factor_research: calc_momentum, calc_volatility, calc_value を実装
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - Volatility / Liquidity: 20 日 ATR、相対ATR、平均売買代金、出来高比等
    - Value: PER / ROE（raw_financials から最新財務を取得し prices_daily と組合せ）
    - SQL＋DuckDB ウィンドウ関数中心で計算（外部APIアクセスなし）
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装
    - calc_forward_returns: 将来リターン計算（horizons の妥当性チェックあり）
    - calc_ic: Spearman（ランク相関）で IC 計算（有効レコード < 3 の場合は None を返す）
    - rank: 同順位は平均ランクで処理（丸めによる ties 検出を安定化）
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）

### 変更 (Changed)

- 初回リリースのため履歴上の変更はありません。

### 修正 (Fixed)

- 初期実装。リリース前に発見された API 呼び出しの再試行やレスポンスパースの不整合に対するフォールバックを追加済み（LLM 失敗時の安全なデフォルト等）。

### 非推奨 (Deprecated)

- なし

### 削除 (Removed)

- なし

### セキュリティ (Security)

- .env 読み込み時に OS 環境変数を保護する設計（.env の不注意な上書きを防止）。
- OpenAI API キーは引数で注入可能であり、明示的に環境変数から取得する実装となっている（テストやキー管理での柔軟性を確保）。

---

注意事項（実装上の重要点・運用メモ）
- AI モジュールは OpenAI の JSON Mode / gpt-4o-mini を前提に設計されています。API 仕様変更やモデル変更時はレスポンスパース周りの影響を受けます。
- DuckDB を前提とする SQL 実行パスが多く、DuckDB のバージョン差分（特に executemany の挙動）に注意が必要です。コード内に互換性対策のコメントがあります。
- ルックアヘッドバイアス対策として、日付参照は target_date 引数ベースで行い、datetime.today()/date.today() を直接参照しない設計を徹底しています（ただし calendar_update_job は実行日の取得に date.today() を使用）。
- LLM 呼び出し失敗時はフェイルセーフ（0.0 フォールバックやその銘柄のスキップ）を行い、ETL やスコアリング処理が全体停止しないようにしています。
- テスト容易性のため、内部で OpenAI 呼び出しをまとめた関数（_call_openai_api）を用意しており、ユニットテストでパッチしやすい設計です。

貢献者:
- 初回実装（詳細なコントリビューター情報はリポジトリ管理者にて管理してください）。