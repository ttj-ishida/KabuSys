Keep a Changelog
================

すべての注目すべき変更はここに記載します。フォーマットは「Keep a Changelog」に準拠します。

v0.1.0 - 2026-03-29
-------------------

Added
- パッケージ初回リリース。
  - パッケージ情報:
    - src/kabusys/__init__.py: バージョン __version__ = "0.1.0"、公開モジュール一覧を定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理:
  - src/kabusys/config.py:
    - .env ファイル（.env/.env.local）または OS 環境変数から設定を自動ロードする機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索するため CWD に依存しない。
    - 読み込みの挙動: OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export 構文、クォート／エスケープ、インラインコメント（空白直前の #）等に対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル等のプロパティとバリデーションを実装。
    - 必須環境変数未設定時は ValueError を送出する _require を用意。
- AI（自然言語処理）機能:
  - src/kabusys/ai/news_nlp.py:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信し、銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ: 前日15:00 JST 〜 当日08:30 JST を UTC に変換して扱う calc_news_window を提供。
    - バッチサイズ、記事数・文字数上限、JSON レスポンス検証、スコアの ±1.0 クリップ等の細かな挙動を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、API 失敗時はスキップし継続（フェイルセーフ）。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（_call_openai_api を patch 可能）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出にマクロキーワードリストを利用し、タイトルを LLM（gpt-4o-mini, JSON Mode）で評価。API 失敗時は macro_sentiment=0.0 とするフェイルセーフを採用。
    - 再試行ロジック、500系の扱い、JSON パースエラーに関する取り扱いを明確化。
    - ルックアヘッドバイアスを避ける設計（date 比較は target_date 未満、datetime.today() を参照しない等）。
- Research（ファクター計算・特徴量探索）:
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金／出来高比率）、バリューファクター（PER/ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱い（十分なウィンドウがない場合は None を返す）や、スキャン範囲のバッファ設計を明記。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応・入力検証）、IC（Information Coefficient）計算（calc_ic、Spearman の ρ 実装）、ランク変換（rank、同順位は平均ランク）、カラム統計サマリ（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB クエリだけで動作するよう実装。
  - src/kabusys/research/__init__.py:
    - 上記関数群をエクスポート（zscore_normalize は kabusys.data.stats から再利用）。
- Data（データ基盤・ETL・カレンダー）:
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar テーブルを利用）と営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日非営業）を採用。DB 登録があれば DB 値を優先し、未登録日は曜日フォールバックで一貫して補完。
    - calendar_update_job を実装（J-Quants API から差分取得して保存、バックフィル、健全性チェック）。
    - 最大探索日数やバックフィル日数等の安全制約を導入し無限ループを防止。
  - src/kabusys/data/pipeline.py:
    - ETL 処理の設計に基づくパイプラインユーティリティを実装。
    - 差分更新、保存（jquants_client の idempotent な save_* を想定）、品質チェック（quality モジュール）を統合する設計方針を含む。
    - ETLResult dataclass を定義（取得・保存数、品質問題一覧、エラー列挙、has_errors/has_quality_errors、辞書化 to_dict を提供）。
    - DuckDB の互換性（テーブル存在チェックや MAX 日付取得のヘルパ）に配慮。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポート（公開インターフェース）。
  - DB 周りの設計方針:
    - DuckDB 0.10 互換の注意（executemany の空リスト不可など）に配慮した実装。
- 互換性・テスト設計上の配慮:
  - 多くのモジュールで外部 API 呼び出し（OpenAI, J-Quants 等）を隠蔽し、テスト時に差し替えられるように設計（_call_openai_api の patch 等）。
  - ルックアヘッドバイアス防止のため、date/datetime の取得は呼び出し側の引数 target_date に依存する一貫した方針を採用。
- ロギングとフェイルセーフ:
  - 各所で警告/情報/例外ログを追加し、API 障害やデータ不足時のフォールバック（中立スコア・スキップなど）を採用して安定動作を重視。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Security
- 初期リリースのため該当なし。

Notes / 実装上の重要な設計決定
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode（厳密な JSON 出力指定）での利用を前提とした設計。
- API 失敗時は基本的に例外を上位へ投げずにフェイルセーフ（0.0 やスキップ）で継続する箇所が多く、監視側での検出・通知を想定。
- DuckDB を第一選択の DB として使用。SQL は可読性と互換性を重視して記述。
- datetime.today()/date.today() の直接参照はほぼ排除し、target_date ベースで処理することでバックテストや再現性に配慮。

今後の予定（未実装だが想定される拡張）
- strategy / execution / monitoring の具備（現在 __all__ に含まれるが実装は別途）。
- より細かな品質チェックルールやモニタリング・アラート機能の充実。
- OpenAI モデルやレイテンシ最適化、キャッシュ戦略の導入。

もし CHANGELOG に追記すべき差分や、リリース日（上のリリース日）は別途指定したい場合は教えてください。