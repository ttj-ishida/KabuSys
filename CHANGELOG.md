Keep a Changelog に準拠した形式で CHANGELOG.md を作成しました。以下はコードベース（バージョン __version__ = "0.1.0"）から推測してまとめた初回リリース向けの変更履歴です。

CHANGELOG.md
-------------

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠しています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------
Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージの公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 環境設定/ロード機能
  - 環境変数読み込みユーティリティを追加（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動検出して読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
    - export KEY=val 形式やクォート / エスケープ、インラインコメント処理を考慮した .env パーサを実装。
    - OS 環境変数を保護する protected 機能（.env.local での上書き制御）。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別等をプロパティ経由で取得。
    - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）を実装。

- AI（自然文処理 / レジーム判定）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - DuckDB の raw_news / news_symbols テーブルを集約して銘柄ごとに記事を結合。
    - OpenAI (gpt-4o-mini) を JSON モードで呼び出して銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄／チャンク）、記事・文字数トリム、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証ロジック（JSON 抽出、results 配列検証、コード整形、数値検査、スコアのクリップ）。
    - 書き込みは idempotent に ai_scores テーブルを DELETE → INSERT（部分失敗時に既存レコードを保護）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - calc_news_window ユーティリティを提供（JST ベースのニュースウィンドウを UTC naive datetime に変換）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照し、計算結果を冪等に market_regime テーブルへ保存（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは専用の実装（news_nlp とは共有しない）でモジュール結合を抑制。
    - API 失敗時はマクロセンチメントを 0.0 とするフェイルセーフを採用。リトライ・バックオフを実装。

- データ管理（Data platform）
  - JPX マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日判定ユーティリティを実装。
    - market_calendar が存在しない場合は曜日（土日）ベースのフォールバックを採用。
    - calendar_update_job により J-Quants API から差分取得 → 保存（バックフィル、健全性チェック、冪等保存）を実装。
    - 最大探索日数やバックフィル日数など安全パラメータを設定して無限ループや極端な未来日付を防止。

  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（src/kabusys/data/etl.py で再エクスポート）。
    - 差分更新・backfill の考え方、J-Quants クライアント（jq）経由での idempotent 保存、品質チェック（quality モジュール）を踏まえた設計。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装。

- 解析/リサーチ機能（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時は None を返す設計（安全に欠損を扱う）。
    - 結果は (date, code) キーの dict リストで返却。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ 相当、スピアマンランク相関）。
    - rank / factor_summary（基本統計量計算）等のユーティリティを実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。

- モジュールエクスポート整理
  - ai、research、data パッケージで主要関数・ユーティリティを __all__ で明示的に公開。
  - src/kabusys/ai/__init__.py で score_news を公開。
  - src/kabusys/research/__init__.py で主要解析関数群を公開。
  - src/kabusys/data/etl.py で ETLResult を公開。

- 実装上の設計方針・品質考慮点（ドキュメント化）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装方針（全て target_date を明示的に受け取る）。
  - OpenAI 呼び出しでの JSON モード利用、レスポンスバリデーション、失敗時のフェイルセーフ（スコア 0.0 やスキップ）を採用。
  - DuckDB の executemany の制約（空リスト不可）に対する防御コードを追加。
  - テスト容易性のため外部 API 呼び出し部分（_call_openai_api 等）を差し替え可能に設計。

Changed
- 初回リリースのため該当なし（新規追加のみ）。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- OpenAI API キーは環境変数 OPENAI_API_KEY か各関数の api_key 引数で指定する必要がある。未指定時は ValueError を送出する。
- 実際の J-Quants / kabu ステーション / Slack クライアント実装や外部 I/O の挙動は jquants_client 等の他モジュールに依存するため、環境や API レスポンスに応じた追加実装・テストが必要。
- 一部モジュールファイル（例: strategy, execution, monitoring）がパッケージ __all__ に名前として含まれているが、本リリースでの実装は限定的のため将来的な追加を想定。
- 日付/時間は UTC naive の datetime を使用する箇所があるため、実運用でのタイムゾーン扱いや DB の calendar 保存形式との整合性確認が必要。

---

上記は提供されたソースコードの内容とドキュメント文字列から推測して作成した CHANGELOG です。追加のコミット履歴や実際のリリース日があれば日付や内容を調整できます。必要であれば英語版やさらに詳細なリリースノート（各ファイル単位の変更点や API 仕様の抜粋）も作成します。