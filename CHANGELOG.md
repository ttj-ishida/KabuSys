# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
重大な内部実装の注意点やフェイルセーフ挙動も併記しています。

※バージョン番号はパッケージの __version__ を参照しています。

## [0.1.0] - 2026-03-31

### Added
- パッケージ初期リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を実装。
  - パッケージメタ情報
    - src/kabusys/__init__.py にてバージョン "0.1.0" と公開モジュール（data, strategy, execution, monitoring）を定義。

- 環境設定 / ロード処理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env の高度なパーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応）。
    - 読み込みの優先順位: OS 環境 > .env.local > .env（.env.local は override）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - Settings クラスによる環境変数ラッパ（J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境種別・ログレベル検証など）。未設定の必須変数は ValueError を送出。

- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - ニュースの銘柄別センチメント算出機能（OpenAI gpt-4o-mini を JSON Mode で使用）。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応）、記事集約（銘柄ごとに最新記事を限度内で結合・トリム）を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、レスポンス検証、スコア ±1.0 でクリップ。
    - 再試行（429 / 接続断 / タイムアウト / 5xx）を指数バックオフで実装。致命的でない失敗はスキップして処理継続（フェイルセーフ）。
    - テスト用に内部の OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch を想定）。
    - DB 書き込みは冪等性を意識（該当コードのみ DELETE → INSERT）。DuckDB の executemany の挙動に配慮し空リストを回避。

  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定モジュール：ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定。
    - ma200_ratio 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを回避。
    - マクロニュースの抽出はキーワードベース。一致記事が無ければ LLM 呼び出しを行わず macro_sentiment=0.0 を採用。
    - OpenAI 呼び出しは再試行ロジック（バックオフ）を実装し、API 失敗時は安全に 0.0 にフォールバック。
    - market_regime テーブルへの書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を担保し、失敗時は ROLLBACK を試行して例外を伝播。

- データプラットフォーム機能（DuckDB ベース）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar）の取得・夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し冪等保存を実施。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない/未登録日は曜日ベースのフォールバック（週末は非営業日扱い）。探索上限を設定して無限ループを防止。
    - バックフィル、先読み、健全性チェック（将来日付の異常検知）を実装。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL パイプラインの骨格実装（差分取得、IDempontent 保存、品質チェックのフレームワーク）。
    - ETLResult データクラスを定義（取得件数・保存件数・品質問題・エラー一覧など）。to_dict により品質問題をシリアライズ可能。
    - デフォルトのバックフィル動作やカレンダー先読みロジックを備える。
    - _table_exists / _get_max_date 等の DB ユーティリティを提供。

- Research（リサーチ）機能
  - src/kabusys/research/factor_research.py
    - ファクター計算実装：モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER・ROE の算出）を提供。
    - DuckDB の SQL ウィンドウ関数を活用し、欠損やデータ不足時は None を返すことで堅牢性を確保。
    - すべて prices_daily / raw_financials を参照し外部 API へアクセスしない安全設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（複数ホライズンをサポート、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - 外部依存せず標準ライブラリのみでアルゴリズムを実装。

- テスト・運用を意識した設計上の備考
  - OpenAI 呼び出し部分はモジュール単位で差し替え可能（ユニット検証を容易にする）。
  - LLM / 外部 API の失敗はシステム全体の停止につながらないようフォールバックやスキップで対処。
  - DuckDB への書き込みはトランザクションで保護し、ROLLBACK の失敗は警告ログ出力で通知。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 外部 API キーは Settings 経由で環境変数から取得する設計。必須キーが未設定の場合は明示的にエラーを発生させる。

---

Contributors: 実装チーム（ソースコード内の author 情報がないため省略）。

注: 本 CHANGELOG は提供されたコードベースから推測して記載しています。将来のコミットで機能追加・修正が行われた場合は適宜更新してください。