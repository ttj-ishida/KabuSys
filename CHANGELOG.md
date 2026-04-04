Changelog
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠します。

注意
----
このCHANGELOGは与えられたコードベースの内容から推測して作成したもので、実際のリリース履歴ではありません。

Unreleased
----------
（今後の変更をここに記載）

[0.1.0] - 2026-04-04
--------------------

Added
- 初期リリース: KabuSys — 日本株自動売買／リサーチ用ライブラリ群を追加。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0, パブリックモジュールの __all__ を定義。
- 環境変数・設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - 自動ロードの探索はパッケージファイル位置基準でプロジェクトルート（.git または pyproject.toml）を特定して行うため、CWD に依存しない。
  - .env パーサを実装:
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを処理。
    - クォートなし値のインラインコメント処理を実装（直前が空白/タブの場合のみ '#...' をコメントとみなす）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書きを防止。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - 必須設定取得ヘルパ _require と Settings クラスを提供。
  - Settings に以下のプロパティを実装（デフォルトやバリデーション含む）:
    - J-Quants / kabu / LINE / DB パス（duckdb/sqlite）/監視用 pid/kill フラグ / CPU/MEM/DISK 閾値 / 環境（development/paper_trading/live）/ログレベル 等。
    - KABUSYS_ENV と LOG_LEVEL に対する値検証（不正値は ValueError）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ保存する処理を実装。
  - タイムウィンドウ（JST基準）計算: 前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して DB クエリに使用。
  - API バッチ処理（1コール最大 20 銘柄）、1銘柄あたりの記事数上限・文字数トリムでトークン肥大化を抑制。
  - JSON Mode による厳密 JSON レスポンスの期待とレスポンス復元ロジック（前後余計なテキストが混ざった場合に {} を抽出してパース）。
  - リトライポリシー: 429・ネットワーク断・タイムアウト・5xx に対し指数バックオフで再試行。その他エラーはスキップしフェイルセーフ。
  - レスポンスバリデーション: results 配列／各要素の code と score チェック、未知コードの無視、スコアの数値変換と ±1.0 クリップ。
  - DuckDB の executemany 空リスト制約を考慮して部分的に DELETE → INSERT を行い、部分失敗時に既存データの保護を実装。
  - テスト容易性: OpenAI 呼び出し関数を差し替え可能に実装（unittest.mock.patch 想定）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判定し market_regime テーブルへ保存する機能を追加。
  - マクロニュース抽出のためのキーワードリスト定義（日本・米国・グローバル系）。
  - OpenAI 呼び出しに対するリトライとフェイルセーフ（API エラーやパース失敗時は macro_sentiment=0.0 として続行）。
  - レジームスコア合成ロジック（スケーリング・クリップ）、および冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - テスト容易性のため OpenAI 呼び出しを差し替え可能な内部関数で抽象化。

- 研究・ファクター計算（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER、ROE）を DuckDB 上の SQL で計算する関数を提供。
    - データ不足時の None ハンドリング、戻り値は (date, code) をキーとする dict のリスト。
    - 計算用ウィンドウ・スキャン日数の定数を定義し、週末・祝日を吸収するバッファを考慮。
  - feature_exploration:
    - 将来リターン calc_forward_returns（デフォルト horizons=[1,5,21]）を実装。horizons の検証（正の整数・252 以下）。
    - IC（スピアマンのランク相関） calc_ic 実装。3 件未満で None を返す。
    - rank（同順位は平均ランク）および factor_summary（count/mean/std/min/max/median）実装。
    - pandas 等の外部ライブラリを使わず、標準ライブラリと DuckDB のみで実装。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。DB データがない場合は曜日ベースでフォールバック。
    - カレンダー夜間バッチ（calendar_update_job）: J-Quants API から差分取得し冪等に保存（バックフィルおよび健全性チェック含む）。
    - 最大探索日数制約（_MAX_SEARCH_DAYS）など無限ループ防止の安全設計。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約）を公開。
    - ETL パイプラインの設計方針とユーティリティ（差分更新、バックフィル、品質チェックの取り扱い方針）を実装。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティ等を実装。
  - jquants_client との連携を前提とした設計（差分取得・保存・品質チェックの流れを想定）。

Security
- OpenAI API キーなどの機密情報は環境変数で取得する設計。必須項目未設定時は ValueError を送出して早期に知らせる。

Design decisions / Notes
- ルックアヘッドバイアス対策: すべての日時ベース処理は datetime.today()/date.today() を直接参照しないよう設計（target_date に依存）。
- フェイルセーフ性: 外部 API エラー発生時は可能な限り処理を継続し、ゼロ値／スキップで安全にフォールバックする。
- テスト性: OpenAI 呼び出し等は差し替え可能（モック化）に実装。
- 互換性: DuckDB API の仕様（executemany に空リストが渡せない等）に対するワークアラウンドを実装。
- 外部依存を最小化: 研究モジュールは pandas 等に依存せず、標準ライブラリのみで実装。

Known limitations
- OpenAI（gpt-4o-mini）を利用する機能は API キーが必須。未設定時は明確なエラーを返す。
- 一部計算（例: PBR、配当利回り）は現バージョン未実装（note として明記）。
- jquants_client / kabu API クライアントの具体的実装・接続はこのコードスニペットには含まれていないが、呼び出し箇所を想定して設計されている。

---
参考: Keep a Changelog — https://keepachangelog.com/ja/1.0.0/