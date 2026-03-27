CHANGELOG
=========
All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.
※ 日付はリリース時点のものです。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-27
--------------------

Added
- パッケージ初回リリース。パッケージ名: kabusys、バージョン: 0.1.0
  - src/kabusys/__init__.py にて公開モジュールを定義 (data, strategy, execution, monitoring)。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込み。
    - 読み込み優先度: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント等に対応。
    - override / protected オプションにより OS 環境変数を保護して .env.local で上書きする挙動を実装。
  - 必須環境変数取得のヘルパー _require と各種プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、DB パス等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）と便利な is_live/is_paper/is_dev プロパティ。

- AI（NLP）モジュール (src/kabusys/ai)
  - ニュースセンチメント分析 (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込み。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して比較）。
    - バッチサイズ、記事数・文字数上限、JSON Mode を用いた厳密なレスポンス期待と検証ロジック。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンス検証とスコアの ±1.0 クリップ、部分成功時に既存データを保護する慎重な DB 書き換え（DELETE→INSERT の idempotent 操作）。
    - テスト容易性を考慮し _call_openai_api を patch 可能に設計。
    - 公開関数: score_news(conn, target_date, api_key=None)。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次で市場レジーム(bull/neutral/bear)を判定。
    - マクロ記事抽出（キーワードベース）、OpenAI 呼び出し、フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - レジームスコアのクリップとラベル決定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- Data / ETL / カレンダー (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティ。
    - market_calendar が存在しない場合の曜日ベースのフォールバックを実装。
    - calendar_update_job により J-Quants API から差分取得し market_calendar を冪等更新。バックフィル、健全性チェック（将来日付の異常検出）を実装。
    - DB マップと曜日フォールバックの組合せで、DB がまばらな場合でも一貫性のある挙動を確保。

  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を導入し、ETL 実行結果（取得数・保存数・品質問題・エラー）を構造化して返却可能に。
    - 差分取得ロジックの基礎ユーティリティ（テーブル存在確認、最大日付取得など）。
    - backfill の概念、品質チェックとの連携設計（品質問題は収集して呼び出し元で判断）。
    - etl モジュール外部公開インターフェースとして ETLResult を再エクスポート。

  - その他データユーティリティ
    - jquants_client と連携する想定（fetch/save 関数を利用する設計）。

- Research（因子解析） (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離等のモメンタム計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等のボラティリティ・流動性計算。
    - calc_value: raw_financials から EPS/ROE を用いて PER/ROE を計算（最新報告書を銘柄別に取得）。
    - DuckDB を用いた SQL 主導の計算、データ不足時の None ハンドリング。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 将来リターン（任意ホライズン）を安全に計算する汎用関数。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外・最小サンプルチェック）。
    - rank: 平均ランク（タイ付き）を返す実装（丸めによる tie 対応）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー。
  - 研究用ユーティリティの公開 (src/kabusys/research/__init__.py) により主要関数をエクスポート。

- 一貫した設計方針（全体）
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today() / date.today() を参照しない設計（target_date を明示的に受け取る）。
  - フェイルセーフ重視: 外部 API 失敗時は例外を投げずにフェイルバック（0 / スキップなど）して処理継続する箇所がある。
  - テスト容易性: OpenAI 呼び出しや内部 API 呼び出しを patch しやすいよう分離。
  - DuckDB を主要なローカル DB として使用。DB 書き込みは可能な限り冪等に設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- なし

Removed
- なし

Security
- 環境変数に依存する API キーやトークンの扱いに注意することを明記。Settings は必須キー未設定時に ValueError を送出して早期検出する。
- .env 自動ロードでは OS 環境変数を保護する仕組みを実装（protected set）。

Notes / Implementation details
- OpenAI とのやり取りは gpt-4o-mini を想定した JSON Mode（response_format）を使用。レスポンス検証・パース処理を厳密に行い、JSON の前後ノイズにも対応する実装が含まれる。
- DuckDB の executemany に対する互換性（空リスト禁止）を考慮して条件付きで実行する実装がある。
- 一部のファイルで設計コメントや docstring を豊富に記載しており、外部 API（J-Quants, kabu）や Slack 連携を想定した設定が組み込まれている。

Contributors
- 初回公開（実装者記載なし）

---

今後のリリースで追記する予定:
- テストカバレッジ・CI ワークフローの追加
- strategy / execution / monitoring モジュールの詳細実装とリリースノート
- 性能改善・並列化（OpenAI バッチ呼び出しの最適化等）
- セキュリティに関する運用指針（シークレット管理、ログ出力の制御）