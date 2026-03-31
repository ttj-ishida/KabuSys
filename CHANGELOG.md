CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
主にコードベースから推測される機能追加・改善点・設計上の配慮を記載しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更 / 改善
- Fixed: バグ修正や堅牢化
- Security: セキュリティ関連の変更

[Unreleased]
-------------

（現在のコードベースが v0.1.0 として初期リリース相当であるため、Unreleased は空です）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境設定管理
  - .env ファイルと環境変数の自動読み込み機能を追加（src/kabusys/config.py）。
    - プロジェクトルート判定は .git または pyproject.toml を基準に探索するため、CWD に依存しない実装。
    - .env と .env.local の優先順位管理（OS 環境変数保護機能付き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - export KEY=val 形式、クォート内エスケープ、行内コメントなどを考慮したパーサ実装。
  - Settings クラスで各種設定値をプロパティとして提供（J-Quants / kabu / Slack / DB パス / 監視閾値 / 環境判定など）。
  - 環境変数検証（KABUSYS_ENV／LOG_LEVEL の許容値チェック、必須 env チェック _require）。

- AI モジュール（OpenAI を利用した NLP / レジーム判定）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとのテキストを生成し、OpenAI（gpt-4o-mini）へバッチで送信。
    - チャンク処理（デフォルト 20 銘柄/チャンク）、1 銘柄あたり記事数上限・文字数トリムの実装。
    - JSON Mode を利用した厳格なレスポンス期待とバリデーション（スコアの型・存在チェック、未知コードの無視）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンスパースの冗長対策（JSON 前後の余計なテキストが混じる場合の {} 抽出）。
    - スコアは ±1.0 にクリップ。取得したスコアを ai_scores テーブルへ冪等的（DELETE→INSERT）に書き込み。
    - 単体テストのために _call_openai_api を patch で差し替え可能な設計。
    - calc_news_window ユーティリティを提供（JST 時間窓を UTC naive datetime に変換）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で 'bull' / 'neutral' / 'bear' を判定。
    - prices_daily と raw_news を参照、OpenAI（gpt-4o-mini）呼び出しは専用内部関数で実装してモジュール結合を低減。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）やリトライ処理を実装。
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス対策（datetime.today()/date.today() を直接参照しない設計、prices_daily は date < target_date の排他参照）。

- データプラットフォーム（DuckDB ベースの ETL とカレンダー管理）
  - ETL 結果データクラス ETLResult を公開（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）。
    - 取得件数・保存件数・品質問題・エラーの集約と to_dict 出力。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得・保存・品質チェックのフロー設計（J-Quants client 経由）。
    - backfill_days による再取得、品質チェックの収集（Fail-Fast ではなく報告型）。
    - DuckDB テーブル存在チェックや最終日取得ユーティリティを実装。
  - 市場カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルの夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得して保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の提供。
    - DB データ優先だが、未登録日は曜日ベースのフォールバック（週末除外）で一貫した挙動を実現。
    - 保存は冪等的に行い、バックフィル・健全性チェック（将来日付の異常検出）を実装。
  - jquants_client を通じた fetch/save の呼び出し想定（実装ファイルは外部と連携する設計）。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1m/3m/6m リターン、ma200 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）、Liquidity 指標を計算。
    - SQL を多用した DuckDB での計算実装。データ不足時の None 戻し。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換・統計サマリー（rank, factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - 研究用ユーティリティの公開（src/kabusys/research/__init__.py）。

Changed
- 設計と実装上の方針を明確化（全体）
  - ルックアヘッドバイアス防止のため、日付取得を関数引数に依存する設計へ統一（date.today()/datetime.today() を直接参照しない）。
  - OpenAI 呼び出し部分はテストしやすいように内部関数化し、外部で patch 可能にしている。
  - DuckDB のバージョン差異（executemany の空リスト制約等）を考慮した互換性対応。

Fixed / Hardened
- エラーハンドリングとトランザクション
  - AI モジュールと ETL/DB 書き込みにおいて、例外時は ROLLBACK を試みる実装を追加。ROLLBACK 失敗時は警告ログ出力。
- OpenAI レスポンスの堅牢なパース
  - JSON mode を利用しつつも、稀に前後に余計なテキストが混ざるケースに対して最外の {} を抜き出して復元するフォールバックを実装。
- スコア範囲の明示的クリッピング（±1.0）
  - news_nlp/regime_detector でスコアが想定範囲外にならないようクリッピングを保証。
- 環境変数読み込みの保護
  - .env ロード時に既存 OS 環境変数を保護する protected set を導入し、.env.local は override=True とするが OS 環境は上書きしない。

Security
- API キーの取り扱いについて明示
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を必須とし、未設定時は ValueError を発生させて明示的に処理を止める。
  - 環境変数の自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Implementation details
- DuckDB を主要なオンディスク分析 DB として利用（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等を前提）。
- OpenAI モデルは gpt-4o-mini を想定し、JSON Mode を利用して機械可読レスポンスを得る設計。
- 多くの処理で「フェイルセーフ（API 失敗時はスキップ or 0.0 で継続）」の方針を採用しているため、自動化バッチが停止しにくい設計。
- 単体テスト容易化のため、外部 API 呼び出し箇所は patch で差し替え可能に実装されている（内部関数を分離）。

今後の予定（推測）
- monitoring / execution モジュールの実装および Slack 連携の実稼働通知（config に Slack トークンが定義されているため）。
- jquants_client の具象実装と CI / データ初期ロードスクリプトの整備。
- ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づく追加実装・ユニットテストの充実。

---
注:
- 上記は提供されたソースコードの内容とコメントから推測した CHANGELOG です。実際のコミット履歴とは異なる場合があります。