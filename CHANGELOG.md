# CHANGELOG

すべての重要な変更はこのファイルで管理します。フォーマットは「Keep a Changelog」を準拠しています。

※ この CHANGELOG はリポジトリ内のソースコードから実装内容と設計方針を推測して作成しています。

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。以下の主要機能・モジュールを実装しています。

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報を公開（kabusys.__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD に依存しない）。
  - 高度な .env パーサ実装:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - コメントの扱い（クォート有無での取り扱い差分）。
  - 環境変数保護機能: OS 環境変数を保護する `protected` セットを用いた .env 上書き制御。
  - Settings クラスを提供（プロパティで各種設定を取得）:
    - J-Quants / kabuステーション / Slack / DB パス（duckdb / sqlite）/実行環境 (development/paper_trading/live) / ログレベル の取得・検証。
    - 無効な env 値や未設定の必須キーで明確な ValueError を発生。

- AI 関連 (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチセンチメント評価。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive で扱う）。
    - バッチ処理・トリミング: 1チャンク最大 20 銘柄、1銘柄当たり最大 10 記事・3000 文字にトリム。
    - 再試行戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出、"results" 配列構造・型検査、未知コードの無視、スコアの ±1.0 クリップ。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT をチャンク単位で実行し、部分失敗時に他コードを保護）。
    - テスト容易性: OpenAI 呼び出しを隠蔽する内部関数を patch 可能（unittest.mock.patch で置換可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動 ETF）の 200 日移動平均乖離とマクロニュース LLM センチメントを重み合成（70% / 30%）して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースの抽出はキーワードリストに基づき raw_news タイトルから取得（最大 20 件）。
    - OpenAI（gpt-4o-mini）を用いた JSON 出力パース、API エラーに対する最大リトライ処理等を実装。
    - API 失敗時は macro_sentiment=0.0 としてフェイルセーフ。
    - market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。
    - テスト用に _call_openai_api を差し替え可能。

- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー（market_calendar）を使った営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバック。
    - next/prev/get_trading_days は DB 登録値優先で未登録は曜日フォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等的に更新（バックフィル・健全性チェック含む）。
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー等を保持）。
    - 差分取得、backfill、品質チェック（quality モジュール）を想定した設計。
    - jquants_client 経由での保存（save_*）を前提とする IDempotent な ETL。
  - etl.py で ETLResult を再エクスポート。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を結合し PER / ROE を計算（EPS が 0/欠損時は None）。
    - すべて DuckDB SQL を用いた実装（DB の prices_daily/raw_financials のみ参照、外部 API なし）。
  - 特徴量評価 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。範囲・入力検証有り。
    - calc_ic: スピアマンのランク相関（IC）計算（結合・None 除外・有効レコード 3 未満で None）。
    - rank: 同順位は平均ランクで扱うランキング関数（丸めで tie を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

### 修正 (Fixed)
- OpenAI レスポンスのパース耐性を強化
  - JSON モードでも前後に余計なテキストが混入するケースで最外の { ... } 部分を抽出して復元する処理を追加。
  - レスポンスパース失敗や JSONDecodeError、型エラー発生時に例外を伝播させず警告ログを出してフェイルセーフ（空スコアや macro_sentiment=0.0 にフォールバック）。
- DuckDB 互換性対応
  - executemany に空リストを渡せない（DuckDB 0.10 等）問題に対するガード条件を追加（空時は実行しない）。
  - 日付を扱う際の型安定化（_to_date ユーティリティ）を追加。

### セキュリティ (Security)
- 環境変数上書き時に OS 環境値を保護
  - .env をロードする際、既存の OS 環境変数は protected セットとして上書きされないように保護。
- API キー未設定時は明確にエラーを出す（ValueError）ため、誤った環境での無自覚な API 呼び出しを防止。

### テスト性 (テスト補助)
- OpenAI 呼び出しを内部関数でラップしているため、ユニットテストで簡単にモック可能（unittest.mock.patch を想定）。
- score_news / score_regime などは api_key を引数で注入可能（環境依存度を下げる）。

### 設計上の注意点 / 既知の制約
- ルックアヘッドバイアス対策として、datetime.today()/date.today() を参照しない設計の関数が多い（target_date を明示的に受け取る）。
- OpenAI は gpt-4o-mini の JSON Mode を利用する想定。API レートリミットや 5xx などはリトライしても最終的に安全側にフォールバックする。
- データベース操作は冪等性を重視（DELETE→INSERT、ON CONFLICT 想定等）。
- 一部の外部モジュール（jquants_client, quality）への依存があるため、本ライブラリ単独では完全に動作しない API 層がある。

### 廃止予定 (Deprecated)
- なし（初回リリースのため該当なし）。

### 削除 (Removed)
- なし（初回リリースのため該当なし）。

---

開発/運用上の補足:
- デフォルトの DB パスは duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db。必要に応じて環境変数で上書き可能。
- ログレベルや実行環境（development/paper_trading/live）は Settings で検証され、不正値は ValueError を返します。
- 今後のリリースでは strategy / execution / monitoring モジュールの詳細実装・互換性ポリシー・マイグレーション手順を追記予定です。