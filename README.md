# KabuSys

KabuSys は日本株の自動売買システムを想定した Python パッケージの骨組みです。データ取得、売買戦略、注文実行、監視の各モジュールを分離して実装できるように設計されています。

現在のバージョン: 0.1.0

---

## プロジェクト概要
KabuSys は日本株の自動売買フレームワークのベースとなるパッケージです。以下の主要コンポーネントを想定しています。

- data: データ取得・前処理（板情報、約定履歴、OHLC 等）
- strategy: 売買戦略（シグナル生成、リスク管理）
- execution: 注文の送信・約定管理（API ラッパー、注文追跡）
- monitoring: 稼働状況・ログ・アラートの監視

現在はパッケージの骨組み（モジュール構成とバージョン情報）が用意されている状態です。各モジュールの具体実装はこれから追加していく想定です。

---

## 機能一覧
現状（0.1.0）ではパッケージ構成のみ提供しています。今後実装が想定される主要機能は以下です。

- データ取得
  - 株価（OHLC）、板情報、約定履歴の取得
  - 過去データのキャッシュ／前処理（欠損補完、正規化）
- 戦略
  - テクニカル指標（移動平均、RSI 等）
  - シグナル生成・ポジション管理・リスク制御
- 注文実行
  - 証券会社 API（kabuステーション等）への注文送信
  - 注文ステータス管理、再試行ロジック
- 監視
  - ログ、メトリクス、障害通知（Slack/メール等）
  - 稼働ダッシュボード（簡易）

---

## セットアップ手順

前提
- Python 3.8 以上を推奨

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境の作成（任意）
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. パッケージのインストール（開発時）
   ```
   pip install -e .
   ```
   ※ 依存パッケージがある場合は `pyproject.toml` または `setup.cfg` / `requirements.txt` を用意して `pip install -r requirements.txt` 等でインストールしてください。

4. バージョン確認
   Python REPL やスクリプトからバージョンを確認できます。
   ```python
   import kabusys
   print(kabusys.__version__)  # 0.1.0
   ```

---

## 使い方（例）

下記は各モジュールの典型的な使い方イメージです。現時点では具体的な API は実装されていませんので、実装時に合わせて修正してください。

- パッケージインポートとバージョン確認
  ```python
  import kabusys
  print(kabusys.__version__)
  ```

- モジュールの想定利用例（擬似コード）
  ```python
  # データ取得
  from kabusys.data import DataClient
  data_client = DataClient(api_key="xxx")
  ohlc = data_client.get_ohlc("7203", period="1d", count=100)

  # 戦略
  from kabusys.strategy import Strategy
  strategy = Strategy(params={...})
  signal = strategy.generate_signal(ohlc)

  # 注文実行
  from kabusys.execution import Executor
  executor = Executor(auth_token="yyy")
  if signal == "BUY":
      executor.place_order("7203", side="BUY", qty=100)

  # 監視
  from kabusys.monitoring import Monitor
  monitor = Monitor()
  monitor.log_trade(...)
  monitor.alert_if_needed(...)
  ```

上記クラス/関数は現状ダミーです。実装時は API の詳細（クラス名、メソッド、例外処理等）をドキュメント化してください。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ構成（現状）:

- src/
  - kabusys/
    - __init__.py         # パッケージ定義（__version__ 等）
    - data/
      - __init__.py
      # データ取得関連コードを配置
    - strategy/
      - __init__.py
      # 戦略ロジックを配置
    - execution/
      - __init__.py
      # 注文実行関連コードを配置
    - monitoring/
      - __init__.py
      # 監視・ログ関連コードを配置
- README.md
- setup.cfg / pyproject.toml (任意で配置)
- requirements.txt (必要に応じて)

簡易ツリー（現在の状態）
```
src/kabusys/__init__.py
src/kabusys/data/__init__.py
src/kabusys/strategy/__init__.py
src/kabusys/execution/__init__.py
src/kabusys/monitoring/__init__.py
```

---

## 開発ガイド（補足）
- テスト
  - 単体テストや統合テストを `tests/` ディレクトリに追加することを推奨します（pytest 等）。
- パッケージ化
  - setuptools / pyproject.toml を用いてパッケージ配布設定を行ってください。
- セキュリティと秘密情報管理
  - API キーや認証情報は環境変数または安全なシークレット管理を利用し、リポジトリに含めないでください。
- ロギング
  - Python の logging モジュールを用いてログを統一的に出力することを推奨します。

---

必要であれば、README に含める具体的な API ドキュメント（関数／クラス一覧やサンプル実装）を生成します。どのモジュールから先に実装したいか教えてください。