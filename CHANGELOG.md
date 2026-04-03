CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
リリース履歴はコードベースから推測して作成しています。

[0.1.0] - 2026-04-03
-------------------

Added
- 初回公開 (kabusys v0.1.0)
  - パッケージのメタ情報
    - __version__ = "0.1.0"
    - パッケージレベルのエクスポート: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装
    - 自動ロードの探索はパッケージ内の __file__ を起点に .git または pyproject.toml を探してプロジェクトルートを特定（CWD 非依存）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応
    - .env 読み込み時、既存 OS 環境変数は protected として上書きから保護
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得
    - J-Quants / kabu API / LINE / DB パス / 監視設定（PID・kill flag）/閾値（CPU/MEM/DISK）等をプロパティで取得
    - 必須値取得用の _require() を実装し、未設定時は ValueError を送出
    - KABUSYS_ENV（development / paper_trading / live） と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）のバリデーションを実施
    - is_live / is_paper / is_dev のユーティリティプロパティを提供

- AI（自然言語処理）モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news, news_symbols テーブルから指定ウィンドウ（JST 基準: 前日 15:00 〜 当日 08:30） の記事を銘柄ごとに集約
    - 1 銘柄当たり最大記事数・最大文字数でトリム（トークン肥大化対策）
    - OpenAI（gpt-4o-mini）の JSON Mode を用いて最大 20 銘柄 / 1 チャンクでバッチ評価
    - エラー耐性: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ、その他はスキップして継続
    - レスポンスを厳密にバリデーション（JSON 抽出、"results" の存在、code/score の型チェック、既知コードのみ採用）
    - スコアは ±1.0 にクリップ
    - 書き込みは部分失敗に配慮した冪等処理（対象コードのみ DELETE → INSERT、DuckDB executemany の空リスト回避）
    - score_news(conn, target_date, api_key=None) を公開。API キー未設定時は ValueError。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（Nikkei 225 連動型）の直近 200 日終値を用いた MA200 乖離（重み 70%）と
      マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - マクロ記事はキーワードでフィルタ（複数の日本語/英語キーワードを定義）
    - OpenAI（gpt-4o-mini）呼び出しは専用の軽量ラッパーを使用、リトライとフォールバック（失敗時 macro_sentiment=0.0）
    - スコア合成はクリップ済みで閾値によりラベル付け（BULL_THRESHOLD / BEAR_THRESHOLD）
    - 書き込みは market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK を試行して上位へ例外を伝播
    - score_regime(conn, target_date, api_key=None) を公開。API キー未設定時は ValueError。

- Data（データプラットフォーム）モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX マーケットカレンダーの管理ロジック（market_calendar テーブル）を提供
    - 営業日関連ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装
    - DB に登録がない日付は曜日ベースのフォールバック（土日は非営業日）
    - 最大探索範囲を設定して無限ループを防止
    - 夜間バッチ calendar_update_job(conn, lookahead_days=90) を実装し、J-Quants API から差分取得して保存（バックフィル・健全性チェックあり）
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult dataclass を公開（取得数・保存数・品質問題・エラーなどを保持）
    - 差分更新・バックフィル・品質チェックの設計（品質問題は収集して呼び出し元で判断）
    - jquants_client を利用した fetch/save の一貫処理を想定
    - デフォルト設定: 最小データ開始日、カレンダー先読み、バックフィル日数などの定数を定義

- Research（リサーチ）モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム: 約1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - ボラティリティ/流動性: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - バリュー: PER（price / EPS、EPS が 0 または欠損時は None）、ROE（raw_financials から）
    - DuckDB 上でウィンドウ関数を駆使して計算し、(date, code) ベースの dict リストを返す
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 (calc_forward_returns): 指定ホライズンの将来終値を LEAD で取得してリターンを算出。horizons の検証あり
    - IC 計算 (calc_ic): スピアマンランク相関（ランク化は独自実装）、有効レコードが 3 未満なら None を返す
    - rank / factor_summary: 重複ランクの平均処理、各カラムの count/mean/std/min/max/median 集計を実装
    - 外部ライブラリに依存せず、標準ライブラリと DuckDB だけで実装

Other
- 全体設計上の注意点（共通）
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() に依存しない設計を採用（target_date を明示的に与える）
  - OpenAI 呼び出しは慎重に扱い、API エラー時はフェイルセーフ（ゼロスコア or スキップ）で処理を継続
  - データベース書き込みは可能な限り冪等になっており、部分失敗時に既存データを不必要に消さない設計
  - DuckDB を主たるデータストアとして想定（SQL + ウィンドウ関数で処理を実装）

Fixed / Changed / Removed / Security
- 初回リリースのため該当なし（N/A）

注記
- 上記はソースコードから推測した機能と仕様の要約です。実運用上の詳細な挙動（API レスポンスの詳細、DB スキーマ、外部依存のバージョン制約など）は実際のドキュメントやコードのコメント、テストを参照してください。