CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

- なし

0.1.0 - 2026-04-01
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py: __version__ = "0.1.0", __all__ に主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py
    - .env および .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env 解析機能を実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
    - 読み込み時の override / protected（OS 環境変数保護）ロジックを実装。
    - 必須環境変数取得ヘルパ _require と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 監視しきい値 / 環境・ログレベル検証等）。
- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - JST 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数・文字数のトリム制御、JSON Mode を利用した API 呼び出し。
    - 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ再試行。レスポンスバリデーション、スコアの ±1.0 クリップ。
    - 部分成功に配慮した DB 書き換え（対象コードのみ DELETE → INSERT）と、DuckDB executemany の空リスト制約への対応。
    - テスト用フック: API 呼び出し関数 _call_openai_api をパッチ可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを排除。
    - マクロニュース取得・LLM 解析（gpt-4o-mini）を実装。API 失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - レジームスコア合成、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト用に _call_openai_api を差し替え可能。
  - src/kabusys/ai/__init__.py で公開 API を整理（score_news を公開）。
- Data / ETL / カレンダー
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理: market_calendar テーブルを用いた営業日判定機能（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB データがない場合は曜日ベース（土日非営業日）でフォールバック。DB 登録値が存在する場合は優先。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル・健全性チェック、save 関数呼び出し）。
    - 最大探索日数やバックフィル日数などの安全パラメータを備え、過度なループや異常な将来日付を防止。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの概要実装とユーティリティ関数群。
    - ETLResult dataclass を追加（取得数、保存数、品質問題、エラーの集約）。to_dict により品質問題をシリアライズ可能。
    - 差分取得・バックフィル、品質チェック（quality モジュール）と非致命性の扱い方針を反映。
    - DB テーブル存在確認や最大日付取得ユーティリティを実装。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。
  - src/kabusys/data/__init__.py を作成（パッケージ構成）。
- Research（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum、Volatility、Value、Liquidity 等の定量ファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時の None 扱い）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
      - calc_value: raw_financials から最新財務データを取り出し PER, ROE を計算。
    - DuckDB ベースの SQL 実行で、prices_daily / raw_financials のみ参照（本番取引 API へはアクセスしない）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定日からの将来リターン計算（複数ホライズン対応、入力検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。データ不足（<3 件）の場合は None。
    - rank: 同順位は平均ランクで処理するランク関数（丸めによる ties の検出ロバスト化）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - src/kabusys/research/__init__.py で上記関数群を公開。
- 監視・その他
  - Settings に監視用 PID ファイルパスや CPU/メモリ/ディスクのしきい値を追加（監視モジュールと連携可）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL）を厳密に行う（不正値は ValueError）。

Changed
- n/a（初期リリースのため「追加」が主体）

Fixed
- n/a（初期リリースのため「修正」はなし）

Notes / Implementation details（設計上の重要点）
- ルックアヘッドバイアス防止
  - AI モジュール・ETL・研究モジュール等のすべてで datetime.today()/date.today() を直接参照せず、呼び出し元から target_date を受け取る設計を採用。
- フェイルセーフ設計
  - OpenAI 呼び出し失敗時やレスポンスパース失敗時は例外を上げず代替値（0.0 など）で継続する箇所が多く、バッチ処理全体の堅牢性を優先。
- テストフレンドリー
  - OpenAI API 呼び出し箇所は内部関数化して unit test から差し替え可能にしている。
- DuckDB 互換性
  - executemany の空リストバインド回避や、日付値の変換ユーティリティなど DuckDB の実装差分に配慮した実装を行っている。

今後の予定（参考）
- strategy / execution / monitoring パッケージの具体的な実装（初期公開ではパッケージ名を露出）。
- 追加の品質チェックルール、より詳細なログとメトリクスの導入。
- OpenAI 呼び出しのコスト最適化やローカル ML バックアップの検討。

---

この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。