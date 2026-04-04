KEEP A CHANGELOG形式に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードベースから推測できる追加機能・設計方針・修正点を記載しています。

保持方針:
- 重要な機能追加は Added
- バグ修正・耐障害性向上は Fixed
- 設計上の注意・内部的な改善は Changed / Internal

------------------------------------------------------------
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/
------------------------------------------------------------

Unreleased
- なし

0.1.0 - 2026-04-04
------------------
Added
- パッケージ初回リリース (kabusys v0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に公開。

- 環境変数/設定管理
  - robust な .env ローダーを実装 (src/kabusys/config.py)
    - プロジェクトルートを .git または pyproject.toml から探索して自動で .env/.env.local を読み込む仕組みを導入（パッケージ配布後も CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数はデフォルトで保護（上書きされない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env 行パーサーは次をサポート:
      - 行頭の "export " プレフィックス
      - シングル/ダブルクォート内のバックスラッシュエスケープ
      - クォートなし行のインラインコメント取り扱い（直前が空白/tab の場合のみコメントと見なす）
  - Settings クラスを提供:
    - J-Quants / kabu API / LINE / DB ファイルパス / 監視しきい値 / 環境 (development/paper_trading/live) / ログレベル 等のプロパティを環境変数から取得・検証。
    - 必須設定が未設定の場合は明確な ValueError を送出。

- ニュース NLP & 市場レジーム判定（AI 統合）
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント (ai_score) を算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算（UTC 変換済み）。
    - チャンク処理（最大20銘柄／回）、1銘柄あたり最大記事数と文字数でトリム。
    - 失敗耐性: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。その他はスキップして継続。
    - レスポンスの厳密なバリデーション (JSON 抽出/構造検査/数値チェック) とスコアの ±1.0 クリップ。
    - ai_scores テーブルへの冪等書き込み（対象コードのみ DELETE → INSERT）。DuckDB の executemany 空リスト制約に配慮。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
  - regime_detector モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動）の 200 日移動平均乖離 (ma200_ratio) とマクロ経済ニュース LLM センチメントを合成して日次の市場レジームを判定（'bull'/'neutral'/'bear'）。
    - マクロ記事はキーワードベースで抽出し、最大件数で LLM に渡す。LLM 呼び出しは独立実装でモジュール結合を避ける。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 としてフェイルセーフに継続。
    - レジームスコア合成と閾値判定（重み: MA70% / MACRO30%、スコアクリップ）。
    - market_regime テーブルへの冪等的トランザクション書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- リサーチ / ファクター計算
  - research パッケージ公開関数 (src/kabusys/research/*.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を算出。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などの計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出。最新報告日以前の財務データを利用。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に取得。horizons のバリデーションあり。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。サンプル不足時は None を返す。
    - rank: 平均ランク処理（同順位は平均ランク）、浮動小数丸めで ties の検出精度向上。
    - factor_summary: count/mean/std/min/max/median の統計要約を標準ライブラリのみで実装。
  - 設計方針: DuckDB のみ参照、外部ライブラリに依存しない、安全な数値/欠測処理。

- データプラットフォーム (Data)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベースでフォールバック。DB がまばらでも一貫した振る舞いを保証。
    - calendar_update_job: J-Quants API (jquants_client) から差分取得 → 保存。バックフィル・健全性チェックを備える。
    - 最大探索範囲 (_MAX_SEARCH_DAYS) により無限ループを防止。
  - ETL パイプライン (src/kabusys/data/pipeline.py / etl.py)
    - ETLResult dataclass を公開（pipeline.ETLResult を再エクスポート）。
    - ETLResult に品質チェック結果・エラー一覧を格納するフィールド、has_errors / has_quality_errors / to_dict を実装。
    - 差分取得、バックフィル日数、品質チェックの扱い方針（Fail-Fast ではなく検出のみ）を実装設計に反映。

Fixed
- .env パースの堅牢化
  - クォート・エスケープ・コメント処理の改善により様々な .env フォーマットに対応。
- DuckDB 書き込み操作の互換性対策
  - executemany に空リストを渡すと失敗する点を考慮して条件付きで実行する実装に変更（ai_scores 等）。

Changed / Internal
- 汎用的な設計方針を採用
  - すべての時刻判定処理やスコア算出は datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス防止）。target_date を明示的に渡す設計。
  - OpenAI 呼び出しはモジュール間でプライベート実装を共有しない（テストで差し替えやすくするため）。
  - API呼び出しの失敗は基本的にスキップして継続する（フェイルセーフ）、ただし重要な環境設定がない場合は明示的に例外を投げる。
- ロギング・監視用設定
  - CPU/MEM/DISK のしきい値・PID/KILL ファイルパスなど監視設定を環境変数で指定できるようにした。

Security
- 必須 API キー（OpenAI など）が未設定の場合は ValueError を発生させ明確に通知する実装を採用（誤動作防止）。

Notes / Known limitations
- OpenAI SDK（gpt-4o-mini）依存。テスト時は _call_openai_api をモックする想定。
- news_nlp/regime_detector は LLM の出力を JSON モードで想定しているが、万一の余剰テキストに対しては復元ロジック（最外の {} を抽出）で耐性を持たせている。
- 一部モジュール（例: strategy, execution, monitoring）は __all__ に含まれているが、本差分ではそれらの詳細実装は含まれていない（将来追加予定）。
- DuckDB のバインドやバージョン差分による制約（配列バインド等）に注意しているため、互換性のある実装を選択。

リリースに含まれる主なファイル（抜粋）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/ai/regime_detector.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/data/calendar_management.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/etl.py

今後の予定（候補）
- strategy / execution / monitoring の実装詳細追加（実際の発注ロジック、監視デーモン等）
- テストスイート整備（DuckDB のインメモリ設定、OpenAI 呼び出しモック）
- ドキュメント（API リファレンス、運用手順、.env.example の整備）

------------------------------------------------------------
以上。必要があれば、各機能についてさらに細かい変更ログ（関数単位）やリリースノート用の英語版も作成します。