Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

[Unreleased]
-----------

（なし）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初回リリース: kabusys v0.1.0
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージ API のトップレベルエクスポートに data, strategy, execution, monitoring を用意。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルートは .git / pyproject.toml から検出）。
    - .env のパースロジックを実装（コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD フラグをサポート。
    - 環境変数上書き挙動（.env と .env.local の優先度）と OS 環境変数保護（protected keys）を実装。
    - Settings クラスを追加し、J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベル等のプロパティとバリデーションを提供。
      - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証を実装。
      - 必須設定未定義時は明示的な ValueError を送出。

- AI（自然言語処理）モジュール
  - src/kabusys/ai/news_nlp.py
    - news スコアリング機能 score_news を実装。raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供（UTC ナイーブ datetime で返却）。
    - 1銘柄あたりの最大記事数・文字数トリム、バッチング（最大 20 銘柄／API コール）、リトライ（429/ネットワーク断/タイムアウト/5xx）と指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造、未知コード無視、数値変換、数値の有限性チェック、±1.0 でクリップ）。
    - API 呼び出し部分は _call_openai_api として切り出し、テスト用に patch しやすい設計。
    - API 失敗時は該当チャンクをスキップし続行するフェイルセーフ設計。

  - src/kabusys/ai/regime_detector.py
    - 市場レジーム判定 score_regime を実装。ETF(1321) の直近 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成し、regime_score / regime_label(bull/neutral/bear) を market_regime テーブルへ冪等書き込みする。
    - MA 算出は target_date 未満のデータのみを使用してルックアヘッドバイアスを避ける設計。
    - OpenAI 呼び出しは独自の _call_openai_api を用い、API 失敗時は macro_sentiment=0.0 にフォールバックする設計。
    - ロギング、リトライ、JSON パースの失敗処理を備える。

  - src/kabusys/ai/__init__.py
    - score_news をエクスポート。

- データ関連（Data Platform）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理機能を提供（market_calendar テーブルを参照/更新）。
    - 営業日判定 API: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB 登録の有無に応じた「DB 優先・未登録は曜日ベースフォールバック」ロジック。
    - calendar_update_job を実装し、J-Quants API（jquants_client 経由）から差分取得・バックフィル・健全性チェック（未来日付閾値）を行って保存する処理を提供。
    - 検索範囲上限（_MAX_SEARCH_DAYS）やバックフィル日数などの安全対策を実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプライン用ユーティリティと ETLResult dataclass を実装。
    - 差分取得、保存（idempotent）、品質チェック（quality モジュール連携）を想定した API 設計。
    - ETLResult は品質問題・エラーの集約、has_errors / has_quality_errors / to_dict を提供。

  - src/kabusys/data/etl.py
    - ETLResult を再エクスポート（パブリックインターフェース）。

  - DuckDB 向けの互換性対策
    - executemany に空リストを渡さない安全処理（DuckDB 0.10 の制約に対応）。

- リサーチ（ファクター計算 / 特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー系のファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）
      - calc_volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率 等
      - calc_value: PER（price / EPS）、ROE（最新の財務データ）を計算
    - DuckDB SQL を活用し、必要な過去データを窓関数で取得する設計。データ不足時の None ハンドリング。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: target_date から指定ホライズン（営業日ベース）の将来リターンを一括取得できる汎用実装（horizons 引数、バリデーション）。
    - calc_ic: スピアマンランク相関（Information Coefficient）の計算（結合・欠損除外・最小レコード数チェック）。
    - rank: ランク付けユーティリティ（同順位は平均ランク、丸めによる tie 対応）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - すべて標準ライブラリと DuckDB のみで実装（pandas 等非依存）。

  - src/kabusys/research/__init__.py
    - 主要関数とユーティリティを再エクスポート（zscore_normalize を含む）。

Other
- ロギング: 多数のモジュールで情報/警告/デバッグログを適切に出力するよう実装。
- テスト容易性: OpenAI 呼び出しや内部 API 呼び出しを patch 可能な形で分離（_call_openai_api の差し替え等）。
- 設計方針の明示:
  - ルックアヘッドバイアス防止（datetime.today()/date.today() の不随参照を避ける設計を優先）。
  - フェイルセーフ: 外部 API 障害時は例外伝播ではなく安全なデフォルト（0.0 やスキップ）で継続する設計。
  - DuckDB 固有挙動への対処（executemany 空リスト回避等）。

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY で解決。未設定時は明示的にエラーを投げることでキー漏洩や暗黙の挙動を防止。

注意事項 / 既知の設計メモ
- jquants_client（データ取得・保存用）や quality モジュールは参照されるが本 CHANGELOG に含まれるソース一覧に全ては同梱されていない場合があります。実行環境ではそれらの依存実装が必要です。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON mode でやり取りします。実際の API バージョンや SDK による差分がある場合は呼び出し部の調整が必要です。
- DuckDB を使った SQL 実行結果の日付型取り扱いや executemany の互換性に注意してください（コード中で互換性対応を行っています）。

--- 

この CHANGELOG はコードベースの初期リリース向けに、機能・実装上の重要点と設計判断をできるだけ実際のコードから推測してまとめたものです。追加で差分やリリース日、細かい変更履歴等の追記が必要であれば教えてください。