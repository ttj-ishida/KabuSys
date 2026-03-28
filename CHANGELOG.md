# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記録しています。  
<https://keepachangelog.com/ja/1.0.0/>

（注）この CHANGELOG は提示されたソースコードから実装内容を推測して作成した初期リリース向けの要約です。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージバージョン __version__ = "0.1.0" を追加。主要サブパッケージ（data, research, ai, ...）を __all__ に公開。

- 環境設定管理
  - src/kabusys/config.py:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理に対応。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境（development/paper_trading/live） / ログレベル等のプロパティを環境変数から取得・検証するユーティリティを追加。
    - 必須環境変数未設定時は ValueError を発生させる _require() を実装。

- AI（ニュースNLP・レジーム検出）
  - src/kabusys/ai/news_nlp.py:
    - raw_news と news_symbols を使って銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄単位のセンチメント ai_score を算出。
    - 時間ウィンドウの算出（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）や、記事・文字数のトリム（最大記事数／最大文字数）を実装。
    - バッチ処理（最大 20 銘柄/回）、API 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンスのバリデーション・スコアの ±1.0 クリップを実装。
    - スコア結果は ai_scores テーブルへ冪等的に（DELETE → INSERT）保存する。

  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、news_nlp のマクロニュースセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news からのデータ取得、OpenAI によるマクロ記事の JSON レスポンス処理、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しはリトライ／タイムアウト等に対処し、失敗時はマクロセンチメントを 0.0 とするフェイルセーフを採用。
    - ルックアヘッドバイアス防止のため datetime.today() 等を参照せず、target_date 未満のデータのみを使用する設計。

- データ関連（ETL・カレンダー等）
  - src/kabusys/data/pipeline.py:
    - ETL の高レベル設計に基づく ETLResult dataclass を実装し、取得数／保存数／品質問題／エラー概要の集約を可能に。
    - データベース（DuckDB）上の最大日付取得やテーブル存在チェック等のヘルパーを提供。
    - 差分取得・バックフィル（デフォルト backfill 3 日）・品質チェック連携のための基盤を用意。

  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を再エクスポートする公開インターフェースを追加。

  - src/kabusys/data/calendar_management.py:
    - JPX マーケットカレンダー管理（market_calendar テーブル）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - calendar_update_job により J-Quants から差分取得 → 保存（ON CONFLICT DO UPDATE）・バックフィル・健全性チェック（将来日付の異常検知）を実装。
    - DB 未取得期間に対する曜日ベースのフォールバック（主に土日判定）をサポートし、DB 登録値を優先する一貫した挙動を実現。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数群（calc_momentum / calc_volatility / calc_value）を実装。
    - データ不足時の扱い（不足で None を返す）や、スキャン範囲バッファの設計を実装。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns: LEAD を用いた任意ホライズン）、IC（Information Coefficient）計算（スピアマンのランク相関 calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を避け、標準ライブラリ＋DuckDB SQL で実装。

- DuckDB 互換性、DB 書き込みの冪等性
  - 多数のモジュールで BEGIN/COMMIT/ROLLBACK を用いたトランザクションや、部分的更新（DELETE → INSERT）により再実行可能な ETL/スコア保存ロジックを採用。
  - DuckDB の executemany の空リスト制約など、実際の DuckDB バージョン差異への配慮を行っている。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI / 外部 API の API キーは引数注入または環境変数（OPENAI_API_KEY）で解決する方式を採用し、未設定時は ValueError を投げ明確に通知する実装。

### Notes / 設計上の重要点
- ルックアヘッドバイアス防止:
  - AI モジュールやリサーチモジュールは datetime.today()/date.today() を直接参照せず、必ず呼び出し側から target_date を渡す設計。
- フェイルセーフ:
  - OpenAI 呼び出し失敗やレスポンスパース失敗時は例外を上位に投げず（モジュールにより挙動は異なる）、0.0 やスキップで継続する実装が多く含まれる（監視・再試行は上位ジョブで扱う想定）。
- OpenAI 連携:
  - gpt-4o-mini を利用する前提で JSON mode を使い、レスポンスの厳密な JSON 化とパース・バリデーションを行う。LLM の出力不正時に備えた回復ロジックを備える。
- 環境変数自動ロード:
  - .env と .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。.env.local は上書き（override=True）される。
- 未実装・制限:
  - factor_research.calc_value では PBR・配当利回りは未実装（注記あり）。
  - 一部の機能は外部モジュール（jquants_client, quality など）に依存しており、その具体実装は別モジュールに委ねられる。
  - __all__ に含まれる execution / monitoring は示された範囲のソースに未出力（別ファイルで実装されている可能性あり）。

## 既知の TODO / 今後の改善候補
- テストカバレッジの強化（特に OpenAI 呼び出しのモックと DuckDB 周り）。
- news_nlp / regime_detector の性能評価およびプロンプト改良。
- ETL ジョブの CLI / スケジューラ統合（現状はライブラリ機能のみ）。
- ai_scores / market_regime の格納スキーマの拡張（メタ情報・確信度等）。
- パッケージのドキュメント（API 仕様・設定例・運用手順）の整備。

---

（補足）この CHANGELOG は渡されたソースコードの実装内容・設計コメントから推測して作成しています。実際のリリースノートとして利用する場合は、リリース日付・変更点の正確性を実コードの変更履歴（git log 等）と照合して調整してください。