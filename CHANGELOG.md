Keep a Changelog に準拠した形式で、コードベースから推測した初期リリースの変更履歴を日本語で作成しました。

注: 日付は本ドキュメント作成日（2026-04-03）を使用しています。内容はソースコードの実装・コメントから推測しています。

Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従います。  
http://semver.org/

Unreleased
----------

- （未リリースの変更はここに記載）

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージの初期リリース: kabusys v0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0", __all__ エクスポート）

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート
  - .env パーサーの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（スペース/タブ直前の '#' をコメント扱い）
    - 無効行のスキップ
  - 環境変数上書き制御:
    - .env と .env.local の読み込み優先度（OS 環境変数を保護する protected set）
  - Settings クラスによるプロパティ提供:
    - J-Quants / kabuステーション / LINE API / DBパス（DuckDB/SQLite）/監視設定（PID, kill flag）/閾値（CPU/Memory/Disk）など
    - KABUSYS_ENV（development/paper_trading/live）とLOG_LEVELの検証（不正値は ValueError）
    - is_live / is_paper / is_dev のユーティリティ

- データ関連（src/kabusys/data/*）
  - ETL 結果を表す ETLResult データクラス（pipeline.ETLResult をエクスポート）
    - ETL の取得件数・保存件数・品質問題リスト・エラーリストなどを追跡
    - has_errors, has_quality_errors, to_dict を提供
  - pipeline モジュールにて差分取得・保存・品質チェックのための骨格実装
    - backfill の考慮、品質チェックは収集して呼び出し側に委ねる設計
    - DuckDB を前提としたテーブル存在チェックなどのユーティリティ
  - calendar_management モジュール:
    - market_calendar を用いた営業日判定（is_trading_day, is_sq_day）
    - 翌営業日／前営業日取得（next_trading_day, prev_trading_day）
    - 期間内営業日列挙（get_trading_days）
    - calendar_update_job: J-Quants からの差分取得と冪等保存（バックフィル、健全性チェックあり）
    - DB にカレンダー情報がない場合は曜日（土日）ベースのフォールバック
    - 最大探索日数・ルックアヘッド・バックフィル日数等の安全機構

- リサーチ（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算
    - calc_volatility: 20日 ATR、ATR 比率、平均売買代金、出来高比などを計算
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損のときは None）
    - DuckDB 上の SQL で実装し、データ不足時の None 返却やログ出力を考慮
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコード < 3 の場合は None）
    - rank: 同順位は平均ランクを返す（丸めによる ties 対処）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
  - すべて外部ライブラリ（pandas 等）に依存せず、標準ライブラリ + DuckDB で実装

- AI（src/kabusys/ai/*）
  - news_nlp.score_news:
    - raw_news + news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価
    - バッチサイズ、最大記事数、文字数トリム等のトークン肥大化対策を実装
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフリトライ
    - レスポンス検証（JSON 抽出、"results"リスト、コード照合、数値チェック）、スコアの ±1.0 クリップ
    - 成功分のみ ai_scores テーブルへ冪等的に DELETE → INSERT（部分失敗時に既存スコアを保護）
    - news ウィンドウ計算（JST 前日 15:00 〜 当日 08:30 相当の UTC 範囲）を calc_news_window で提供
    - API キー引数または環境変数 OPENAI_API_KEY から取得、未設定時は ValueError を送出
    - テスト用に _call_openai_api をモック可能
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）
    - マクロニュース抽出はマクロキーワード群によるフィルタリング、最大記事数制限あり
    - OpenAI 呼び出しは JSON Mode、リトライ/フォールバックロジック（API 失敗時は macro_sentiment=0.0）
    - レジームスコア合成、閾値に基づくラベル付け、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - lookahead バイアス防止設計（date 引数ベース、datetime.today() を内部で参照しない）
    - API キー注入可能（引数または OPENAI_API_KEY）

- 共通の堅牢化/運用面の実装
  - DuckDB を前提とした SQL 実行およびトランザクション（BEGIN/COMMIT/ROLLBACK）の使用
  - executemany の空リスト問題への対処（DuckDB 互換性考慮）
  - 各所でのログ出力（info/warning/debug/exception）による運用性向上
  - 外部 API 呼び出しに対するフェイルセーフ設計（API 失敗時は処理を続行し、安全なデフォルト値へフォールバック）

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- API キー（OpenAI）未設定時は明示的に ValueError を送出して安全性を担保
- .env 読み込み時に OS 環境変数を保護するため protected set を導入

Notes / 今後の改善点（ソースからの推測）
- 単体テストでは _call_openai_api を patch して外部通信を切り離すことが想定されている
- OpenAI SDK の挙動変化（status_code の有無等）に備えた堅牢化が入っているが、将来的な SDK 変更に合わせた追加対応が必要
- news_nlp/regime_detector のプロンプトやモデルは現状 gpt-4o-mini を利用する設計。運用でのコスト/レイテンシを鑑みた見直しが検討範囲
- DuckDB のバージョン依存や executemany の制約に関して、CI でのバージョン固定・テスト追加が推奨される

Authors
- ソースコード内コメント・実装に基づき作成

以上。必要であれば日付の修正、より詳細な分類（例: モジュール別の小項目分割）や英語版 CHANGELOG の追加も作成します。どの形式に整備したいか指示ください。