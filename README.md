# KabuSys

日本株自動売買システム（スケルトン実装）

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株の自動売買システムのための軽量なパッケージ構成（スキャフォールド）です。データ取得、売買戦略、注文実行、モニタリングの4つの主要コンポーネントを想定したモジュール分割を提供します。現状は骨組みのみの実装ですので、各モジュールに具体的なロジックを実装して拡張して利用してください。

目的:
- 自動売買システム開発のためのディレクトリ構成と基本インターフェースを提供
- 各機能を独立して実装・テストできる設計にすること

---

## 機能一覧（想定）

現在のリポジトリはモジュール構成を提供するのみです。各モジュールに対して任意の実装を追加して利用します。

- data: 市場データ取得（リアルタイム/履歴）
- strategy: 売買戦略ロジックの実装・管理
- execution: 注文発注・約定管理・APIラッパー
- monitoring: ログ、メトリクス、ダッシュボード用の監視処理

注: 上記は想定される責務であり、現状はモジュールのパッケージ定義のみが含まれます。各機能は利用者が実装してください。

---

## 要件

- Python 3.8+
- 必要に応じて各種外部APIクライアントやライブラリ（requests、pandas、numpy など）を追加してください

---

## セットアップ手順

ローカル開発環境でのセットアップ例:

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. パッケージを開発モードでインストール
   ```
   pip install -e .
   ```

4. インストール確認
   ```
   python -c "import kabusys; print(kabusys.__version__)"
   ```
   上記で `0.1.0` が表示されればインストール成功です。

---

## 使い方（開始ガイド）

このパッケージは現状モジュールのスケルトンのみを提供します。以下は、各モジュールに独自実装を追加して利用する際の簡単なテンプレート例です。

1. strategy に戦略クラスを追加する例
   - ファイル: `src/kabusys/strategy/simple.py`
   ```python
   class SimpleStrategy:
       def on_market_data(self, data):
           # data を解析してシグナルを生成
           # シグナルに基づき execution モジュールに注文を依頼する
           pass
   ```

2. execution に注文実行クラスを追加する例
   - ファイル: `src/kabusys/execution/executor.py`
   ```python
   class OrderExecutor:
       def send_order(self, symbol, side, size, price=None):
           # ブローカーAPIへ注文を送信するロジックを実装
           pass
   ```

3. アプリケーションの組み立て例
   ```python
   from kabusys.strategy.simple import SimpleStrategy
   from kabusys.execution.executor import OrderExecutor

   strategy = SimpleStrategy()
   executor = OrderExecutor()

   # 市場データ受信ループ（擬似）
   for data in market_data_stream():
       signal = strategy.on_market_data(data)
       if signal:
           executor.send_order(**signal)
   ```

重要:
- 各モジュールで例外処理や再接続ロジック、レート制限対策を実装してください。
- 実運用前にバックテストやペーパートレードで十分に検証してください。

---

## ディレクトリ構成

現状のディレクトリ構成（主要ファイル）:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py           # パッケージ初期化、__version__ 定義
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
├─ setup.cfg / pyproject.toml   # （プロジェクトに応じて存在）
├─ setup.py                     # （存在する場合）
└─ README.md
```

ソースのエントリポイント:
- `src/kabusys/__init__.py` でパッケージのバージョンや `__all__` を定義しています。

---

## 開発ガイドライン・拡張ポイント

- 各サブパッケージに対して明確なインターフェース（メソッド名・引数・戻り値）を設計してください。
- 単体テスト、統合テストを充実させ、CI 環境で自動実行することを推奨します。
- ログは structured logging（JSON など）やメトリクス（Prometheus など）に出力すると運用が楽になります。
- ブローカーAPIキーや機密情報は環境変数やVault等で安全に管理してください。

---

## 貢献・ライセンス

- このリポジトリはスケルトンです。機能追加・修正のプルリクエストを歓迎します。
- ライセンスはプロジェクト規約に従って設定してください（ここでは未指定です）。

---

以上。何か特定の機能のサンプル実装や、データソース／証券会社APIのラッパー実装例が必要であればお知らせください。具体的なコード例を作成します。