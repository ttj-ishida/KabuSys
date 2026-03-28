CHANGELOG
=========

すべての重要な変更履歴をここに記録します。本ファイルは "Keep a Changelog" に準拠します。

フォーマット:
- Unreleased: 次リリースのための未リリース変更（現状なし）。
- 各リリースは日付付きで「Added / Changed / Fixed / Security / Removed」などのカテゴリで記載します。

Unreleased
----------
- （なし）

[0.1.0] - 2026-03-28
-------------------
Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - __all__ に主要サブモジュールを公開: data, strategy, execution, monitoring

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local をプロジェクトルートから自動ロードする仕組みを実装
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索（CWD 非依存）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
    - OS 環境変数を保護する protected オプションを実装（.env.local は上書き可能だが OS 変数は上書きされない）
    - .env パースは export 形式、クォート文字列、インラインコメント処理、エスケープを考慮
  - Settings クラスを提供し、必須変数の取得（_require）や既定値・検証を行うプロパティを実装
    - J-Quants / kabu ステーション / Slack / DBパス / 環境（development/paper_trading/live） / ログレベル 等
    - 不正な env 値は ValueError を発生させる

- データプラットフォーム（src/kabusys/data/*）
  - カレンダー管理モジュール（calendar_management.py）
    - market_calendar テーブルの存在確認、営業日判定、次/前営業日検索、期間内営業日列挙、SQ 日判定を提供
    - DB に情報があれば DB 値優先。未登録日は曜日ベース（平日）でフォールバック
    - 最大探索期間を設定して無限ループを回避（_MAX_SEARCH_DAYS）
    - calendar_update_job を実装。J-Quants から差分取得して冪等的に保存（バックフィル・健全性チェックあり）
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（etl.ETLResult として re-export）
      - ETL の取得数・保存数・品質問題・エラーメッセージを構造化して保持
      - has_errors / has_quality_errors / to_dict を提供
    - 差分取得、バックフィル、品質チェック等を想定したユーティリティを実装
    - DuckDB のテーブル存在チェック、最大日付取得などのユーティリティ関数を実装

  - jquants_client / quality 等に接続するための手続き的構造（実装は別ファイルを前提）

- AI モジュール（src/kabusys/ai/*）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとに記事を結合して OpenAI（gpt-4o-mini）でセンチメントを評価
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたり記事数/文字数の上限設定、JSON Mode レスポンスのバリデーションを実装
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。不可逆エラーはスキップ（フェイルセーフ）
    - レスポンスの検証ロジック（results 配列、code の正規化、数値チェック、スコア ±1.0 でクリップ）
    - ai_scores テーブルへ冪等的に書き込む（対象コードのみ DELETE → INSERT）
    - テスト容易性のため _call_openai_api を patch で差し替え可能
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）と
      マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（bull/neutral/bear）
    - prices_daily と raw_news を参照して ma200_ratio を計算、ニュースはマクロキーワードでフィルタして LLM に投げる
    - OpenAI 呼び出しは独自実装（news_nlp と private 関数を共有しない設計）
    - API 失敗時は macro_sentiment = 0.0 でフォールバック、全体のスコアは [-1,1] にクリップ
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装
    - リトライや 5xx 判定など、堅牢なエラー処理を実装
    - テスト用に _call_openai_api をモック可能

- Research（src/kabusys/research/*）
  - ファクター計算群を実装（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを計算
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（PBR/配当は未実装）
    - DuckDB + SQL ウィンドウ関数中心の実装。返却は辞書のリスト形式（date, code を含む）
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用した一括取得）
    - calc_ic: スピアマンランク相関（Information Coefficient）計算（ランクは同順位平均ランク）
    - rank: 値列をランク列に変換（小数丸めで ties を安定化）
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）
  - research パッケージ __init__ で主要関数を公開

- 共通ユーティリティ/設計上の配慮
  - ルックアヘッドバイアス防止: 各 AI/研究モジュールは datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計
  - DuckDB を主要なローカル分析 DB として利用
  - エラー耐性: API 失敗は基本的にフェイルセーフ（デフォルト値で継続）し、重要な DB 書き込み失敗時のみ例外を伝播
  - テストしやすさ: OpenAI 呼び出し等は内部関数を patch で差し替え可能に実装
  - 明確な上限/既定値: バッチサイズ、リトライ回数、スコアクリップ範囲などを定数化して可読性・保守性を確保
  - SQL 実装は DuckDB 互換性を考慮（executemany の空リスト回避や ROW_NUMBER / WINDOW 句の利用）

Security
- 環境変数の扱いに配慮
  - 自動 .env ロードで OS 環境変数を保護（.env の上書きを防止する機構）
  - 必須の API キー系は未設定時に明確な ValueError を投げる

Known limitations / Notes
- OpenAI の API 実装は gpt-4o-mini + JSON Mode を前提としており、将来の SDK 変更に備えてエラーの status_code を慎重に参照している
- news_nlp は PBR や配当利回りなど一部ファクターを未実装
- jquants_client, quality などの外部連携関数は本コード上で呼び出す前提だが、実際の API クライアント実装は別ファイル（または外部）になる想定
- DuckDB バージョン依存の挙動（executemany の空リストなど）を回避するためのガードが実装されている

Footer
------
- 以降のリリースでは、下記のカテゴリに沿って更新予定です: Added / Changed / Deprecated / Removed / Fixed / Security
- バグ修正や API 変更、パフォーマンス改善、研究/戦略の追加等は次バージョンで記載します。