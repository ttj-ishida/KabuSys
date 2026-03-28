# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在の安定バージョン: 0.1.0

[0.1.0] - 2026-03-28
====================

Added
-----
- パッケージ初期リリース。
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール: data, strategy, execution, monitoring

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local ファイルまたは OS 環境変数から設定を読み込む自動ローダを実装。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - プロジェクトルートの検出は __file__ を起点に `.git` または `pyproject.toml` を探索（CWD 非依存）。
  - .env パーサは以下をサポート:
    - 空行・コメント行（先頭 #）の無視
    - `export KEY=val` 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - 非クォート値の行内コメント処理（直前が空白/タブの場合のみ）
  - 環境変数保護機能: OS 環境変数を保護する `protected` 機構と `override` オプション。
  - Settings クラスを提供し、よく使う設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパープロパティ: is_live, is_paper, is_dev

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存。
    - 対象ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC で変換して DB クエリに使用）。
    - バッチ処理: 最大 20 銘柄ずつ送信、1 銘柄あたり最大記事数（10 件）、最大文字数（3000 文字）でトリム。
    - JSON Mode を利用した厳密パースとレスポンス検証（results フィールド、code/score の型検査、未知コード無視）。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - API キーは引数で注入可能（api_key）。未指定時は環境変数 OPENAI_API_KEY を参照。
    - 処理はフェイルセーフ設計: API エラーや検証失敗時は当該チャンクをスキップし、他チャンクは継続。
    - DuckDB 用に部分的な冪等書き込み（DELETE → INSERT）を採用し、部分失敗時に既存データを保護。
    - テスト容易性のため API 呼び出し関数を patch 可能に設計（_call_openai_api を差し替え可能）。
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロニュースはマクロキーワードでフィルタし、OpenAI に JSON 出力を要求してパース。
    - API リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）。
    - 判定結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時にロールバック処理。
    - API キーは引数で注入可能（api_key）。未指定時は環境変数 OPENAI_API_KEY を参照。

- データプラットフォーム関連 (kabusys.data)
  - ETL パイプライン基盤 (kabusys.data.pipeline)
    - ETLResult dataclass を導入（target_date, fetched/saved counts, quality_issues, errors 等）。to_dict で監査ログ向け辞書化。
    - 差分取得、バックフィル、品質チェックの設計方針とユーティリティを実装。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。
  - ETL 公開 API (kabusys.data.etl)
    - pipeline.ETLResult を再エクスポート。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX マーケットカレンダーを扱うユーティリティ群を追加:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合は曜日ベース（平日が営業日）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル、健全性チェック（未来日付の異常検知）を実装。
    - 最大検索範囲を設定して無限ループを防止。

- Research / ファクター計算 (kabusys.research)
  - ファクター計算モジュールを提供:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR / 相対 ATR / 平均売買代金 / 出来高比率。
    - calc_value: PER（EPS が 0/欠損なら None）, ROE（raw_financials から取得）。
  - 特徴量探索・統計 (kabusys.research.feature_exploration)
    - calc_forward_returns: 将来リターン（任意ホライズン、デフォルト [1,5,21]）を一括取得。
    - calc_ic: ランク相関による Information Coefficient（Spearman ρ）計算。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとするランク関数（浮動小数の丸めで ties の扱いを安定化）。
  - utils 再エクスポート: zscore_normalize を data.stats から再エクスポート。
  - 実装方針: DuckDB と標準ライブラリのみを使用、ルックアヘッドバイアス回避（date.today() 参照禁止）を徹底。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Known Limitations / Notes
-------------------------
- OpenAI API の利用が前提（gpt-4o-mini を想定）。API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。
- 一部フィールド（例: PBR、配当利回り）は現バージョンで未実装（calc_value に注記あり）。
- DuckDB への executemany は空リストを受け付けない制約を考慮した実装になっている（互換性対策）。
- news_nlp / regime_detector 内の OpenAI 呼び出しはテスト用に差し替え可能（_call_openai_api を patch）。
- .env パーサは多くの一般的ケースに対応するが、非常に特殊なフォーマットの行はパースできない可能性あり。

セキュリティ
------------
- 環境変数の読み込み実装において OS 環境変数を保護する仕組みを導入（.env による上書き制御）。
- 外部 API（J-Quants / OpenAI）呼び出しはリトライおよびフェイルセーフで設計。HTTP レスポンスの 5xx は適切にリトライ対象とするロジックを実装。

今後の予定（例）
----------------
- 追加のファクター（PBR、配当利回り等）の実装。
- 発注・実行モジュール（strategy / execution / monitoring）の具体実装の拡充。
- テストカバレッジの強化および CI パイプライン構築。

--------------------
（本 CHANGELOG はリポジトリ内のソースコードと docstring から推測して自動生成した要約です。実際の変更履歴やリリースノートは運用方針に合わせて調整してください。）